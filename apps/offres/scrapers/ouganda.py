"""Appels d'offres de l'Ouganda (eGP, Government Procurement Portal).

Source : https://egpuganda.go.ug/bid-notices, une seule page HTML. Chaque
ligne : reference et entite acheteuse (lien vers la fiche
/index/<n>_egp), type, objet (tronque par le site), publication, echeance.
"""

import re
from datetime import date

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import UG_URL, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0"}


def texte(el) -> str:
    return " ".join(el.get_text(" ").split()) if el else ""


def normalize(ligne) -> dict | None:
    cellules = ligne.find_all("td", recursive=False)
    lien = ligne.select_one("a.font-weight-semibold[href]")
    m = re.search(r"/index/(\w+)", lien["href"]) if lien else None
    if len(cellules) < 5 or not m:
        return None
    entite = texte(lien.select_one(".text-muted"))
    reference = texte(lien).removesuffix(entite).strip()
    genre, objet, publie, cloture = (texte(c) for c in cellules[1:5])
    titre = objet or reference
    return {
        "id": f"ug-{m.group(1)}",
        "source": "ouganda",
        "titre": titre,
        "organisation": entite,
        "pays": "Ouganda",
        "date_limite": cloture[:10],
        "date_publication": publie[:10],
        "description": f"{genre}. Ref {reference}. {titre}",
        "lien": lien["href"],
    }


def extraire(html: str) -> list:
    soupe = BeautifulSoup(html, "html.parser")
    return [i for i in map(normalize, soupe.select("table tbody tr")) if i]


class OugandaScraper(BaseScraper):
    source_key = "ouganda"
    nom = "Ouganda (eGP)"
    site = UG_URL

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        nouveaux = [i for i in extraire(get_html(UG_URL, HEADERS, timeout=60))
                    if i["id"] not in seen_ids and i["date_limite"] >= aujourdhui]
        return nouveaux[:limite] if limite else nouveaux
