"""Appels d'offres de LuxDev (agence luxembourgeoise de cooperation).

Source : https://luxdev.lu/en/tenders/call-tenders?page=<n>, liste Drupal de
12 cartes : statut et pays en en-tete, titre (tronque par le site), puis
reference, type et "Deadline: 16.12.2026" en pied.
"""

import re
import time
from datetime import date, datetime

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import (LUXDEV_URL, LUXDEV_BASE, LUXDEV_MAX_PAGES, LUXDEV_PAGE_DELAY,
                           FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0"}


def spans(el) -> list:
    return [" ".join(s.get_text(" ").split()) for s in el.select("span") if s.get_text(strip=True)] if el else []


def normalize(carte) -> dict | None:
    lien, titre = carte.select_one("a[href]"), carte.select_one("h3")
    tete, pied = spans(carte.select_one("header")), spans(carte.select_one("footer"))
    if not lien or not titre or len(tete) < 2 or not pied:
        return None
    m = re.search(r"Deadline:\s*(\d{2}\.\d{2}\.\d{4})", " ".join(pied))
    reference, genre = pied[0], (pied[1] if len(pied) > 2 else "")
    titre = " ".join(titre.get_text(" ").split())
    return {
        "id": f"luxdev-{reference}",
        "source": "luxdev",
        "titre": titre,
        "organisation": "LuxDev (cooperation luxembourgeoise)",
        "pays": tete[1],
        "statut": tete[0],
        "date_limite": datetime.strptime(m.group(1), "%d.%m.%Y").date().isoformat() if m else "",
        "description": f"{genre}. Ref {reference}. {titre}",
        "lien": LUXDEV_BASE + lien["href"],
    }


def extraire(html: str) -> list:
    soupe = BeautifulSoup(html, "html.parser")
    return [i for i in map(normalize, soupe.select("li.views-row")) if i]


class LuxdevScraper(BaseScraper):
    source_key = "luxdev"
    nom = "LuxDev (Luxembourg)"
    site = LUXDEV_URL

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        nouveaux = []
        for page in range(LUXDEV_MAX_PAGES):
            if page:
                time.sleep(LUXDEV_PAGE_DELAY)
            try:
                cartes = extraire(get_html(LUXDEV_URL, HEADERS, {"page": page}))
            except Exception as exc:
                print(f"LuxDev : page {page + 1} en echec ({str(exc)[:60]}).")
                break
            ouvertes = [c for c in cartes if c.pop("statut") == "Open"
                        and c["date_limite"] >= aujourdhui]
            nouveaux += [c for c in ouvertes if c["id"] not in seen_ids]
            # Echeances decroissantes, et le site laisse "Open" sur des avis echus :
            # la premiere page sans echeance a venir clot la liste.
            if not ouvertes:
                break
        return nouveaux[:limite] if limite else nouveaux
