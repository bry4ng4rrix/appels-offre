"""Appels d'offres federaux du Canada (CanadaBuys / AchatsCanada).

Source : CSV ouvert des avis en cours (licence du gouvernement ouvert du
Canada), une ligne par avis, chaque champ en anglais et en francais. On
retient la version francaise. Les descriptions portent des entites HTML.
"""

import csv
import io
from datetime import date
from html import unescape

from .base import BaseScraper
from .fid import texte_brut
from .http import get
from Offre.sources import CANADA_CSV, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0"}


def normalize(ligne: dict) -> dict | None:
    reference = ligne.get("referenceNumber-numeroReference", "").strip()
    titre = (ligne.get("title-titre-fra") or ligne.get("title-titre-eng") or "").strip()
    if not reference or not titre:
        return None
    region = ligne.get("regionsOfDelivery-regionsLivraison-fra", "").replace("*", "").strip()
    methode = ligne.get("procurementMethod-methodeApprovisionnement-fra", "")
    description = texte_brut(unescape(ligne.get("tenderDescription-descriptionAppelOffres-fra")
                                      or ligne.get("tenderDescription-descriptionAppelOffres-eng") or ""))
    return {
        "id": f"ca-{reference}",
        "source": "canada",
        "titre": titre,
        "organisation": ligne.get("contractingEntityName-nomEntitContractante-fra", ""),
        "pays": "Canada",
        "date_limite": ligne.get("tenderClosingDate-appelOffresDateCloture", "")[:10],
        "date_publication": ligne.get("publicationDate-datePublication", "")[:10],
        "description": ". ".join(x for x in (methode, f"Livraison : {region}" if region else "",
                                             description[:1200]) if x),
        "lien": ligne.get("noticeURL-URLavis-fra") or ligne.get("noticeURL-URLavis-eng", ""),
    }


def extraire(texte: str) -> list:
    return [i for i in map(normalize, csv.DictReader(io.StringIO(texte))) if i]


class CanadaScraper(BaseScraper):
    source_key = "canada"
    nom = "Canada (CanadaBuys)"
    site = "https://canadabuys.canada.ca/fr/occasions-de-marche"

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        texte = get(CANADA_CSV, HEADERS, timeout=120).content.decode("utf-8-sig")
        vus, nouveaux = set(seen_ids), []
        for item in extraire(texte):
            # Un avis modifie revient sur une ligne par modification.
            if item["id"] not in vus and (not item["date_limite"] or item["date_limite"] >= aujourdhui):
                vus.add(item["id"])
                nouveaux.append(item)
        return nouveaux[:limite] if limite else nouveaux
