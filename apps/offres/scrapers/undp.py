"""Avis de marches du PNUD (UNDP Procurement Notices).

Source : https://procurement-notices.undp.org/ -- une seule page HTML porte
tous les avis ouverts (523 au sondage du 17/11/2026), chaque ligne etant un
lien a.vacanciesTableLink : titre, reference, bureau/pays, procedure,
echeance ("29-Nov-26 02:30 AM (New York time)"), publication ("17-Nov-26").
"""

import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import UNDP_URL, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0"}


def texte(el) -> str:
    return " ".join(el.get_text(" ").split()) if el else ""


def date_courte(brut: str) -> str:
    """"29-Nov-26 02:30 AM (New York time)" -> "2026-11-29"."""
    m = re.match(r"\d{1,2}-[A-Za-z]{3}-\d{2}", brut or "")
    try:
        return datetime.strptime(m.group(), "%d-%b-%y").date().isoformat() if m else ""
    except ValueError:
        return ""


def pays(bureau: str) -> str:
    """"UNDP-MDG/MADAGASCAR" -> "Madagascar"."""
    nom = bureau.split("/", 1)[-1].strip()
    return nom.title() if nom.isupper() else nom


def normalize(lien) -> dict | None:
    cellules = [texte(s) for s in lien.select(".vacanciesTable__cell span")]
    m = re.search(r"(nego_id|notice_id)=(\d+)", lien.get("href", ""))
    if len(cellules) < 6 or not m or not cellules[0]:
        return None
    titre, ref, bureau, procedure, echeance, publie = cellules[:6]
    return {
        "id": f"undp-{'n' if m.group(1) == 'notice_id' else ''}{m.group(2)}",
        "source": "undp",
        "titre": titre,
        "organisation": "PNUD (UNDP)",
        "pays": pays(bureau),
        "date_limite": date_courte(echeance),
        "date_publication": date_courte(publie),
        "description": ". ".join(x for x in (procedure, f"Ref {ref}" if ref else "",
                                             f"Bureau {bureau}" if bureau else "", titre) if x),
        "lien": UNDP_URL + lien["href"].lstrip("/"),
    }


def extraire(html: str) -> list:
    soupe = BeautifulSoup(html, "html.parser")
    return [i for i in map(normalize, soupe.select("a.vacanciesTableLink")) if i]


class UndpScraper(BaseScraper):
    source_key = "undp"
    nom = "PNUD (UNDP)"
    site = UNDP_URL

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        nouveaux = [i for i in extraire(get_html(UNDP_URL, HEADERS, timeout=60))
                    if i["id"] not in seen_ids
                    and not (i["date_limite"] and i["date_limite"] < aujourdhui)]
        return nouveaux[:limite] if limite else nouveaux
