"""Avis de marches des projets de la BERD (EBRD), plateforme ECEPP.

Source : https://ecepp.ebrd.com/delta/noticeSearchResults.html, une seule
page avec tout l'historique (~4 100 avis). Colonnes : "Pays: titre", type
d'avis, operation, publication, cloture ("28/12/2026 10:00 UK Time" ou
"N/A"), etat (Open / Closed / Information Only), ..., projet. Seuls les avis
a l'etat "Open" sont retenus.
"""

import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import EBRD_URL, EBRD_FICHE, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0"}


def texte(el) -> str:
    return " ".join(el.get_text(" ").split()) if el else ""


def date_uk(brut: str) -> str:
    m = re.match(r"\d{2}/\d{2}/\d{4}", brut or "")
    return datetime.strptime(m.group(), "%d/%m/%Y").date().isoformat() if m else ""


def normalize(ligne) -> dict | None:
    cellules = ligne.find_all("td", recursive=False)
    lien = ligne.select_one("a[href*=displayNoticeId]")
    m = re.search(r"displayNoticeId=(\d+)", lien["href"]) if lien else None
    if len(cellules) < 6 or not m or texte(cellules[5]) != "Open":
        return None
    pays, _, titre = texte(cellules[0]).partition(": ")
    genre, projet = texte(cellules[1]), texte(cellules[-1]).strip("[]")
    return {
        "id": f"ebrd-{m.group(1)}",
        "source": "berd",
        "titre": titre or pays,
        "organisation": "BERD (EBRD)",
        "pays": pays if titre else "",
        "date_limite": date_uk(texte(cellules[4])),
        "date_publication": date_uk(texte(cellules[3])),
        "description": f"{genre}. Projet {projet}. {texte(cellules[2])}",
        "lien": EBRD_FICHE + m.group(1),
    }


def extraire(html: str) -> list:
    soupe = BeautifulSoup(html, "html.parser")
    return [i for i in map(normalize, soupe.select("tr")) if i]


class BerdScraper(BaseScraper):
    source_key = "berd"
    nom = "BERD (EBRD)"
    site = EBRD_URL

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        nouveaux = [i for i in extraire(get_html(EBRD_URL, HEADERS, timeout=120))
                    if i["id"] not in seen_ids
                    and not (i["date_limite"] and i["date_limite"] < aujourdhui)]
        return nouveaux[:limite] if limite else nouveaux
