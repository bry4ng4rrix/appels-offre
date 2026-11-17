"""Avis de marches des projets de la Banque islamique de developpement.

Source : https://www.isdb.org/project-procurement/tenders?page=<n> (Drupal).
Liste triee par date de cloture croissante, ~50 avis par page : les avis
actifs sont en fin de liste, on lit donc toutes les pages. Chaque article
porte le statut (slug-active / slug-closed), le type, le pays et la cloture
("16 December 2026"). Les attributions de contrat sont ecartees.
"""

import time
from datetime import date, datetime

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import ISDB_URL, ISDB_MAX_PAGES, ISDB_PAGE_DELAY, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0"}


def texte(el) -> str:
    return " ".join(el.get_text(" ").split()) if el else ""


def date_longue(brut: str) -> str:
    try:
        return datetime.strptime(brut, "%d %B %Y").date().isoformat()
    except ValueError:
        return ""


def normalize(article) -> dict | None:
    lien = article.select_one("h2 a[href]")
    statut = article.select_one(".vocabulary-tender-status")
    genre = article.select_one(".vocabulary-tender-type")
    if not lien or not article.get("data-nid"):
        return None
    if not statut or "slug-active" not in statut.get("class", []):
        return None
    if genre and "slug-contract-award" in genre.get("class", []):
        return None
    titre = texte(lien)
    return {
        "id": f"isdb-{article['data-nid']}",
        "source": "isdb",
        "titre": titre,
        "organisation": "Banque islamique de developpement (BIsD)",
        "pays": texte(article.select_one(".field--name-field-world-country")),
        "date_limite": date_longue(texte(article.select_one("time"))),
        "description": f"{texte(genre)}. {titre}" if genre else titre,
        "lien": "https://www.isdb.org" + lien["href"],
    }


def extraire(html: str) -> tuple[list, int]:
    """Avis actifs de la page, et nombre d'articles lus (0 = fin de liste)."""
    articles = BeautifulSoup(html, "html.parser").select(".views-row article")
    return [i for i in map(normalize, articles) if i], len(articles)


class IsdbScraper(BaseScraper):
    source_key = "isdb"
    nom = "Banque islamique de dev."
    site = ISDB_URL

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        nouveaux = []
        for page in range(ISDB_MAX_PAGES):
            if page:
                time.sleep(ISDB_PAGE_DELAY)
            avis, lus = extraire(get_html(ISDB_URL, HEADERS, {"page": page}))
            nouveaux += [a for a in avis if a["id"] not in seen_ids
                         and not (a["date_limite"] and a["date_limite"] < aujourdhui)]
            if not lus:
                break
        return nouveaux[:limite] if limite else nouveaux
