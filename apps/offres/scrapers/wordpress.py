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
from Offre.sources import (CEMAC_API, CEMAC_CATEGORIE, MEDD_API, GRET_API, WP_SOURCES,
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
    #: Champs demandes a l'API (`_fields`).
    champs: str = "id,date,link,title"

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
                    "orderby": "date", "order": "desc", "_fields": self.champs})
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
                # Echeance connue (Coordination SUD) et deja passee : avis clos.
                if item and item["date_limite"] and item["date_limite"] < date.today().isoformat():
                    continue
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


# --- Quatrieme vague (19/11/2026) : organisations regionales, agences, ONG ---

class CeeacScraper(WordpressScraper):
    source_key = "ceeac"
    nom = "CEEAC (Afrique centrale)"
    site = "https://ceeac-eccas.org/"
    api, filtres, prefixe = WP_SOURCES["ceeac"], {"categories": "24,4"}, "ceeac"
    organisation = "Commission de la CEEAC"


class AgrhymetScraper(WordpressScraper):
    source_key = "agrhymet"
    nom = "AGRHYMET (CILSS)"
    site = "https://www.agrhymet.cilss.int/"
    api, filtres, prefixe = WP_SOURCES["agrhymet"], {"categories": 75}, "agrhymet"
    organisation, pays = "Centre regional AGRHYMET (CILSS)", "Niger"


class OapiScraper(WordpressScraper):
    source_key = "oapi"
    nom = "OAPI (propriete intellectuelle)"
    site = "https://www.oapi.int/"
    api, filtres, prefixe = WP_SOURCES["oapi"], {"categories": 3}, "oapi"
    organisation, pays = "Organisation africaine de la propriete intellectuelle", "Cameroun"


class AmrefScraper(WordpressScraper):
    source_key = "amref"
    nom = "Amref Health Africa"
    site = "https://www.amref.org/tenders/"
    api, filtres, prefixe = WP_SOURCES["amref"], {"categories": "41,42"}, "amref"
    organisation = "Amref Health Africa"


class UetclScraper(WordpressScraper):
    source_key = "uetcl"
    nom = "UETCL (electricite, Ouganda)"
    site = "https://www.uetcl.go.ug/"
    api, filtres, prefixe = WP_SOURCES["uetcl"], {"categories": 8}, "uetcl"
    organisation, pays = "Uganda Electricity Transmission Company", "Ouganda"


class AgeturScraper(WordpressScraper):
    source_key = "agetur"
    nom = "AGETUR (travaux, Benin)"
    site = "https://www.agetur.bj/"
    api, filtres, prefixe = WP_SOURCES["agetur"], {"categories": 2}, "agetur"
    organisation, pays = "AGETUR", "Bénin"


class AcbfScraper(WordpressScraper):
    source_key = "acbf"
    nom = "ACBF (renforcement des capacites)"
    site = "https://www.acbf-pact.org/"
    api, prefixe = WP_SOURCES["acbf"], "acbf"
    organisation, pays = "African Capacity Building Foundation", "Zimbabwe"


class SanteSudScraper(WordpressScraper):
    source_key = "sante_sud"
    nom = "Sante Sud (ONG)"
    site = "https://www.santesud.org/"
    api, filtres, prefixe = WP_SOURCES["sante_sud"], {"categories": 24}, "santesud"
    organisation = "Sante Sud"


class FaraScraper(WordpressScraper):
    source_key = "fara"
    nom = "FARA (recherche agricole)"
    site = "https://www.faraafrica.org/"
    api, filtres, prefixe = WP_SOURCES["fara"], {"categories": 98}, "fara"
    organisation, pays = "Forum for Agricultural Research in Africa", "Ghana"


class AsarecaScraper(WordpressScraper):
    source_key = "asareca"
    nom = "ASARECA (recherche agricole)"
    site = "https://www.asareca.org/"
    api, filtres, prefixe = WP_SOURCES["asareca"], {"categories": 90}, "asareca"
    organisation, pays = "ASARECA", "Ouganda"


# --- Cinquieme vague (19/11/2026) : Madagascar, Afrique, ONG ---

class MiasaScraper(WordpressScraper):
    source_key = "miasa"
    nom = "MiASA, Agriculture (Madagascar)"
    site = "https://www.miasa.gov.mg/"
    api, filtres, prefixe = WP_SOURCES["miasa"], {"categories": "114,112,116"}, "miasa"
    organisation, pays = "Ministere de l'Agriculture et de l'Elevage", "Madagascar"


class EducationMadagascarScraper(WordpressScraper):
    source_key = "education_mg"
    nom = "Education nationale (Madagascar)"
    site = "https://www.education.gov.mg/"
    api, filtres, prefixe = WP_SOURCES["education_mg"], {"categories": 66}, "men"
    organisation, pays = "Ministere de l'Education nationale", "Madagascar"


class AderScraper(WordpressScraper):
    source_key = "ader"
    nom = "ADER, electrification rurale (Madagascar)"
    site = "https://www.ader.mg/"
    api, filtres, prefixe = WP_SOURCES["ader"], {"categories": "33,34"}, "ader"
    organisation, pays = "Agence de Developpement de l'Electrification Rurale", "Madagascar"


class CsiMadagascarScraper(WordpressScraper):
    source_key = "csi_mg"
    nom = "CSI, Comite pour la sauvegarde de l'integrite (Madagascar)"
    site = "https://www.csi.gov.mg/"
    api, filtres, prefixe = WP_SOURCES["csi_mg"], {"categories": "42,43"}, "csi"
    organisation, pays = "Comite pour la Sauvegarde de l'Integrite", "Madagascar"


class ComesaScraper(WordpressScraper):
    source_key = "comesa"
    nom = "COMESA"
    site = "https://www.comesa.int/"
    api, filtres, prefixe = WP_SOURCES["comesa"], {"categories": "48,21"}, "comesa"
    organisation, pays = "Secretariat du COMESA", "Zambie"


class CicosScraper(WordpressScraper):
    source_key = "cicos"
    nom = "CICOS (bassin du Congo)"
    site = "https://www.cicos.int/"
    api, filtres, prefixe = WP_SOURCES["cicos"], {"categories": 19}, "cicos"
    organisation, pays = "Commission internationale du bassin Congo-Oubangui-Sangha", "RD Congo"


class TrademarkAfricaScraper(WordpressScraper):
    source_key = "trademark_africa"
    nom = "TradeMark Africa"
    site = "https://trademarkafrica.com/"
    api, filtres, prefixe = WP_SOURCES["trademark_africa"], {"categories": 53}, "tma"
    organisation = "TradeMark Africa"


class SolthisScraper(WordpressScraper):
    source_key = "solthis"
    nom = "Solthis (ONG sante)"
    site = "https://www.solthis.org/fr/appel-doffre/"
    api, prefixe = WP_SOURCES["solthis"], "solthis"
    organisation = "Solthis"


class ActionContreLaFaimScraper(WordpressScraper):
    source_key = "action_contre_la_faim"
    nom = "Action contre la faim (Etats-Unis)"
    site = "https://www.actionagainsthunger.org/"
    api, filtres, prefixe = WP_SOURCES["action_contre_la_faim"], {"categories": 8}, "aah"
    organisation = "Action Against Hunger"


class CoordinationSudScraper(WordpressScraper):
    """Appels d'offres des ONG francaises, publies par elles-memes."""
    source_key = "coordination_sud"
    nom = "Coordination SUD (ONG francaises)"
    site = "https://www.coordinationsud.org/appels-offres/"
    api, prefixe = WP_SOURCES["coordination_sud"], "csud"
    champs = "id,date,link,title,acf"

    def normalize(self, article):
        item = super().normalize(article)
        fin = str((article.get("acf") or {}).get("date-fin") or "")
        if item and len(fin) == 8 and fin.isdigit():       # "20261209"
            item["date_limite"] = f"{fin[:4]}-{fin[4:6]}-{fin[6:]}"
        return item
