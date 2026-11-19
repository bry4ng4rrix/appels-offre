"""Appels d'offres du Rwanda (Umucyo, e-procurement de la RPPA).

Source : formulaire POST selectListAdvertisingListForGU.do (currentPageNo,
recordCountPerPage). Lignes de huit cellules : case, intitule, reference
("000002/G/NCB/2026/2027/RSSB", entite en dernier segment), statut,
invitation, echeance ("07/12/2026 16:00"), ouverture, etapes. Triee par
echeance decroissante. Les fiches s'ouvrent en JavaScript : le lien mene a la liste.
"""

import time
from datetime import date

from bs4 import BeautifulSoup

from .base import BaseScraper
from .berd import date_uk, texte
from .http import post_html
from Offre.sources import RW_URL, RW_PAGE_SIZE, RW_MAX_PAGES, RW_PAGE_DELAY, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0"}
TYPES = {"G": "Goods", "W": "Works", "C": "Consultant services", "NC": "Non-consultant services"}


def normalize(ligne) -> dict | None:
    cellules = [texte(c) for c in ligne.find_all("td", recursive=False)]
    if len(cellules) < 8 or "/" not in cellules[2] or cellules[3] == "Cancelled":
        return None
    titre, reference, statut, publie, cloture = cellules[1:6]
    segments = reference.split("/")
    return {
        "id": f"rw-{reference}",
        "source": "rwanda",
        "titre": titre,
        "organisation": segments[-1],
        "pays": "Rwanda",
        "date_limite": date_uk(cloture),
        "date_publication": date_uk(publie),
        "description": f"{TYPES.get(segments[1], segments[1])}. {segments[2]}. Ref {reference}. "
                       f"{statut}. {titre}",
        "lien": RW_URL,
    }


def extraire(html: str) -> list:
    soupe = BeautifulSoup(html, "html.parser")
    return [i for i in map(normalize, soupe.select("tr")) if i]


class RwandaScraper(BaseScraper):
    source_key = "rwanda"
    nom = "Rwanda (Umucyo)"
    site = RW_URL

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        nouveaux = []
        for page in range(1, RW_MAX_PAGES + 1):
            if page > 1:
                time.sleep(RW_PAGE_DELAY)
            try:
                avis = extraire(post_html(RW_URL, HEADERS, {
                    "currentPageNo": page, "recordCountPerPage": RW_PAGE_SIZE}, formulaire=True))
            except Exception as exc:
                print(f"Rwanda : page {page} en echec ({str(exc)[:60]}).")
                break
            ouverts = [a for a in avis if a["date_limite"] >= aujourdhui]
            nouveaux += [a for a in ouverts if a["id"] not in seen_ids]
            # Echeances decroissantes : la premiere page echue clot le parcours.
            if len(ouverts) < len(avis) or len(avis) < RW_PAGE_SIZE:
                break
        return nouveaux[:limite] if limite else nouveaux
