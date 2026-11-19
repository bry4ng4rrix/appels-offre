"""Subventions federales americaines (Grants.gov).

Source : API publique search2 (POST JSON, sans cle). Une seule requete rend
tous les avis ouverts ("posted"). Dates au format americain MM/JJ/AAAA ;
closeDate est vide pour les appels permanents.
"""

from datetime import date, datetime

from .base import BaseScraper
from .http import post_json
from Offre.sources import GRANTS_GOV_URL, GRANTS_GOV_FICHE, GRANTS_GOV_ROWS, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0", "Content-Type": "application/json"}


def date_us(brut: str) -> str:
    try:
        return datetime.strptime(brut or "", "%m/%d/%Y").date().isoformat()
    except ValueError:
        return ""


def normalize(avis: dict) -> dict | None:
    if not avis.get("id") or not avis.get("title"):
        return None
    return {
        "id": f"grantsgov-{avis['id']}",
        "source": "grants_gov",
        "titre": avis["title"].strip(),
        "organisation": avis.get("agency") or avis.get("agencyCode") or "",
        "pays": "États-Unis",
        "date_limite": date_us(avis.get("closeDate")),
        "date_publication": date_us(avis.get("openDate")),
        "description": f"Subvention federale americaine. Ref {avis.get('number', '')}. "
                       f"{avis['title'].strip()}",
        "lien": GRANTS_GOV_FICHE + str(avis["id"]),
    }


class GrantsGovScraper(BaseScraper):
    source_key = "grants_gov"
    nom = "Grants.gov (Etats-Unis)"
    site = "https://www.grants.gov/search-grants"

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        reponse = post_json(GRANTS_GOV_URL, HEADERS, {
            "rows": GRANTS_GOV_ROWS, "oppStatuses": "posted", "startRecordNum": 0})
        avis = filter(None, map(normalize, (reponse.get("data") or {}).get("oppHits") or []))
        # Sans date de cloture : appel permanent, donc ouvert.
        nouveaux = [a for a in avis if a["id"] not in seen_ids
                    and (not a["date_limite"] or a["date_limite"] >= aujourdhui)]
        return nouveaux[:limite] if limite else nouveaux
