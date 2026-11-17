"""Appels d'offres de la JIRAMA (eau et electricite de Madagascar).

Source : API REST WordPress, categorie "Appels d'offres" (id 135).
L'article ne contient que le lien vers le PDF de l'avis : pas de date de
cloture lisible, on retient les avis publies depuis JIRAMA_MAX_JOURS.
Les rectificatifs, resultats et annulations ne sont pas des appels ouverts.
"""

import re
import time
from datetime import date

from .base import BaseScraper
from .fid import date_publication, sans_accents, texte_brut
from .http import get_json
from Offre.sources import (JIRAMA_API_URL, JIRAMA_CATEGORIE, JIRAMA_MAX_JOURS,
                           JIRAMA_MAX_PAGES, FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "application/json"}
NON_OUVERTS = re.compile(r"rectificatif|modification|resultat|attribution|annulation|infructueux")


def normalize(brut: dict) -> dict | None:
    titre = texte_brut((brut.get("title") or {}).get("rendered", ""))
    publie = date_publication(brut)
    if not titre or NON_OUVERTS.search(sans_accents(titre)):
        return None
    return {
        "id": f"jirama-{brut.get('id')}",
        "source": "jirama",
        "titre": titre,
        "organisation": "JIRAMA",
        "pays": "Madagascar",
        "date_limite": "",
        "date_publication": publie or "",
        "description": f"Publie le {publie}. Avis en PDF sur la page de la JIRAMA. {titre}",
        "lien": brut.get("link", ""),
    }


class JiramaScraper(BaseScraper):
    source_key = "jirama"
    nom = "JIRAMA Madagascar"
    site = "https://www.jirama.mg/category/appel-doffre/"

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        nouveaux = []
        for page in range(1, JIRAMA_MAX_PAGES + 1):
            if page > 1:
                time.sleep(0.5)
            try:
                bruts = get_json(JIRAMA_API_URL, HEADERS, {
                    "categories": JIRAMA_CATEGORIE, "per_page": 50, "page": page,
                    "orderby": "date", "order": "desc", "_fields": "id,date,link,title"})
            except Exception as exc:
                if "400" not in str(exc):          # 400 = au-dela de la derniere page
                    print(f"JIRAMA : page {page} en echec ({str(exc)[:60]}).")
                break
            for brut in bruts:
                publie = date_publication(brut)
                # Tri par date decroissante : passe la fenetre, tout le reste est plus vieux.
                if publie and (date.today() - publie).days > JIRAMA_MAX_JOURS:
                    return nouveaux
                item = normalize(brut)
                if item and item["id"] not in seen_ids:
                    nouveaux.append(item)
                    if limite and len(nouveaux) >= limite:
                        return nouveaux
            if not bruts:
                break
        return nouveaux
