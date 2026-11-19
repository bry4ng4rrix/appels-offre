"""Sites WordPress qui publient leurs appels d'offres en articles.

Meme principe que la JIRAMA : l'API REST rend titre, date et lien, mais
l'echeance n'est que dans le PDF joint. On retient donc les avis publies
depuis `max_jours`, hors rectificatifs, resultats et annulations. Une source
de ce genre se declare en quelques attributs (voir les classes en fin de module).
"""

import time
from datetime import date

from .base import BaseScraper
from .fid import date_publication, sans_accents, texte_brut
from .http import get_json
from .jirama import NON_OUVERTS
from Offre.sources import (CEMAC_API, CEMAC_CATEGORIE, MEDD_API, GRET_API,
                           WP_MAX_JOURS, WP_MAX_PAGES, FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "application/json"}


class WordpressScraper(BaseScraper):
    #: Point d'API : .../wp-json/wp/v2/posts, ou le type dedie (.../appel_offre).
    api: str = ""
    #: Filtres supplementaires, par exemple {"categories": 71}.
    filtres: dict = {}
    prefixe: str = ""
    organisation: str = ""
    pays: str = ""

    def normalize(self, article: dict) -> dict | None:
        titre = texte_brut((article.get("title") or {}).get("rendered", ""))
        if not titre or NON_OUVERTS.search(sans_accents(titre)):
            return None
        publie = date_publication(article)
        return {
            "id": f"{self.prefixe}-{article.get('id')}",
            "source": self.source_key,
            "titre": titre,
            "organisation": self.organisation,
            "pays": self.pays,
            "date_limite": "",
            "date_publication": publie or "",
            "description": f"Publie le {publie}. Avis en piece jointe sur le site. {titre}",
            "lien": article.get("link", ""),
        }

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        nouveaux = []
        for page in range(1, WP_MAX_PAGES + 1):
            if page > 1:
                time.sleep(0.5)
            try:
                articles = get_json(self.api, HEADERS, {
                    **self.filtres, "per_page": 50, "page": page,
                    "orderby": "date", "order": "desc", "_fields": "id,date,link,title"})
            except Exception as exc:
                if "400" not in str(exc):          # 400 = au-dela de la derniere page
                    print(f"{self.nom} : page {page} en echec ({str(exc)[:60]}).")
                break
            for article in articles:
                publie = date_publication(article)
                # Tri par date decroissante : passe la fenetre, tout le reste est plus vieux.
                if publie and (date.today() - publie).days > WP_MAX_JOURS:
                    return nouveaux
                item = self.normalize(article)
                if item and item["id"] not in seen_ids:
                    nouveaux.append(item)
                    if limite and len(nouveaux) >= limite:
                        return nouveaux
            if len(articles) < 50:
                break
        return nouveaux


class CemacScraper(WordpressScraper):
    source_key = "cemac"
    nom = "CEMAC (Afrique centrale)"
    site = "https://www.cemac.int/category/appels-doffres-et-recrutements/"
    api, filtres, prefixe = CEMAC_API, {"categories": CEMAC_CATEGORIE}, "cemac"
    organisation = "Commission de la CEMAC"


class MeddMadagascarScraper(WordpressScraper):
    source_key = "medd"
    nom = "Ministere de l'Environnement (Madagascar)"
    site = "https://www.environnement.mg/appel-offre/"
    api, prefixe = MEDD_API, "medd"
    organisation, pays = "Ministere de l'Environnement et du Developpement Durable", "Madagascar"


class GretScraper(WordpressScraper):
    source_key = "gret"
    nom = "GRET (ONG francaise)"
    site = "https://www.gret.org/appel_doffres/"
    api, prefixe = GRET_API, "gret"
    organisation = "GRET"
