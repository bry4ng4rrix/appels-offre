"""Appels d'offres publics de Nouvelle-Zelande (GETS).

Source : flux RSS de tous les avis ouverts. La description de chaque item est
un tableau HTML echappe : RFx ID, Organisation, Open date, Close date
("Monday, 31 December 2029 5:00 PM +13:00"), Categories (UNSPSC), Region,
Overview.
"""

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get
from Offre.sources import NZ_RSS, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0"}


def champs(description: str) -> dict:
    """{"RFx ID": "32705858", "Close date": "...", ...} depuis le tableau HTML."""
    resultat = {}
    for ligne in BeautifulSoup(description or "", "html.parser").select("tr"):
        cellules = ligne.select("td")
        if len(cellules) >= 2:
            cle = cellules[0].get_text(" ", strip=True).rstrip(" :")
            resultat[cle] = " ".join(cellules[1].get_text(" ").split())
    return resultat


def date_longue(brut: str) -> str:
    """"Monday, 31 December 2029 5:00 PM +13:00" -> "2029-12-31"."""
    m = re.search(r"(\d{1,2} [A-Za-z]+ \d{4})", brut or "")
    try:
        return datetime.strptime(m.group(1), "%d %B %Y").date().isoformat() if m else ""
    except ValueError:
        return ""


def normalize(item) -> dict | None:
    titre = (item.findtext("title") or "").strip()
    c = champs(item.findtext("description"))
    if not titre or not c.get("RFx ID"):
        return None
    return {
        "id": f"nz-{c['RFx ID']}",
        "source": "nouvelle_zelande",
        "titre": titre,
        "organisation": c.get("Organisation", ""),
        "pays": "Nouvelle-Zélande",
        "date_limite": date_longue(c.get("Close date")),
        "date_publication": date_longue(c.get("Open date")),
        "description": ". ".join(x for x in (c.get("Categories", ""), c.get("Overview", "")[:1200]) if x),
        "lien": (item.findtext("link") or "").replace(".nz//", ".nz/"),
    }


def extraire(xml: bytes) -> list:
    return [i for i in map(normalize, ET.fromstring(xml).iter("item")) if i]


class NouvelleZelandeScraper(BaseScraper):
    source_key = "nouvelle_zelande"
    nom = "Nouvelle-Zélande (GETS)"
    site = "https://www.gets.govt.nz/ExternalIndex.htm"

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        nouveaux = [i for i in extraire(get(NZ_RSS, HEADERS, timeout=60).content)
                    if i["id"] not in seen_ids and i["date_limite"] >= aujourdhui]
        return nouveaux[:limite] if limite else nouveaux
