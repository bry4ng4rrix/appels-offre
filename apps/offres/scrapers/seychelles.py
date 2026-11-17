"""Appels d'offres des Seychelles (Procurement Oversight Unit).

Source : https://www.pou.gov.sc/tenders/<rubrique>?start=<n>, 8 avis par
page, rubriques travaux, fournitures et services, consultants. La date de
cloture n'existe que dans le script du compte a rebours :
new Date('2026-12-21T10:00:53+04:00').
"""

import re
import time
from datetime import date

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import SC_URL, SC_RUBRIQUES, SC_MAX_PAGES, SC_PAGE_DELAY, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0"}
RUBRIQUES = {"civil-works": "Civil works", "goods-and-services": "Goods and services",
             "consultancies": "Consultancy"}


def normalize(article, rubrique: str) -> dict | None:
    lien = article.select_one("h2 a[href]")
    m = re.search(r"/(\d+)-", lien["href"]) if lien else None
    if not m:
        return None
    cloture = re.search(r"new Date\('(\d{4}-\d{2}-\d{2})", str(article))
    publie = article.select_one("time[datetime]")
    titre = " ".join(lien.get_text(" ").split())
    return {
        "id": f"sc-{m.group(1)}",
        "source": "seychelles",
        "titre": titre,
        "organisation": "Gouvernement des Seychelles",
        "pays": "Seychelles",
        "date_limite": cloture.group(1) if cloture else "",
        "date_publication": publie["datetime"][:10] if publie else "",
        "description": f"{RUBRIQUES.get(rubrique, rubrique)}. {titre}",
        "lien": "https://www.pou.gov.sc" + lien["href"],
    }


def extraire(html: str, rubrique: str) -> list:
    soupe = BeautifulSoup(html, "html.parser")
    return [i for i in (normalize(a, rubrique) for a in soupe.select(".uk-article")) if i]


class SeychellesScraper(BaseScraper):
    source_key = "seychelles"
    nom = "Seychelles (POU)"
    site = SC_URL + "goods-and-services"

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        nouveaux = []
        for rubrique in SC_RUBRIQUES:
            for page in range(SC_MAX_PAGES):
                time.sleep(SC_PAGE_DELAY)
                try:
                    avis = extraire(get_html(SC_URL + rubrique, HEADERS, {"start": page * 8}), rubrique)
                except Exception as exc:
                    print(f"Seychelles : {rubrique} page {page + 1} en echec ({str(exc)[:60]}).")
                    break
                ouverts = [a for a in avis if a["date_limite"] >= aujourdhui]
                nouveaux += [a for a in ouverts if a["id"] not in seen_ids]
                # Du plus recent au plus ancien : une page sans avis ouvert clot la rubrique.
                if not ouverts or len(avis) < 8:
                    break
        return nouveaux[:limite] if limite else nouveaux
