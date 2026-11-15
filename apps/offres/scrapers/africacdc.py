"""Opportunités de la division Supply Chain d'Africa CDC.

Le portail public sépare les appels de la division Supply Chain et ceux du
African Pooled Procurement Mechanism (APPM). Les tableaux donnent le titre,
la date limite, la référence et le type, avec un lien vers l'avis officiel.
Les critères d'éligibilité restent propres à chaque avis et doivent être
vérifiés dans le dossier avant candidature.
"""

import hashlib
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import AFRICACDC_APPM_URL, AFRICACDC_SUPPLY_URL, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "text/html"}
MOIS_EN = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12,
}


def date_iso(valeur: str) -> str:
    """Convertit une échéance du portail, par exemple ``9 December 2026``."""
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b", valeur or "")
    if not m:
        return ""
    jour, mois_txt, annee = m.groups()
    mois = MOIS_EN.get(mois_txt.lower())
    if not mois:
        return ""
    try:
        return date(int(annee), mois, int(jour)).isoformat()
    except ValueError:
        return ""


def lire_tableau(html: str, url_liste: str) -> list[dict]:
    """Lit les lignes du tableau d'offres courantes sans dépendre des classes CSS."""
    soup = BeautifulSoup(html or "", "html.parser")
    items = []
    for row in soup.select("tr"):
        cells = row.find_all(["td", "th"], recursive=False)
        if len(cells) < 4 or any(cell.name == "th" for cell in cells):
            continue

        lien = cells[0].find("a", href=True)
        if not lien:
            continue
        titre = " ".join(lien.get_text(" ", strip=True).split())
        echeance_txt = " ".join(cells[1].get_text(" ", strip=True).split())
        reference = " ".join(cells[2].get_text(" ", strip=True).split())
        type_avis = " ".join(cells[3].get_text(" ", strip=True).split())
        if not titre or not reference:
            continue

        href = urljoin(url_liste, lien["href"])
        identifiant = hashlib.sha1(f"{reference}|{href}".encode()).hexdigest()[:12]
        items.append({
            "id": f"africacdc-{identifiant}",
            "source": "africacdc",
            "titre": titre,
            "organisation": "Africa CDC",
            # Africa CDC est continental ; Madagascar est membre de l'Union
            # africaine. La notice reste l'arbitre de l'éligibilité effective.
            "pays": "Afrique (Madagascar membre de l'Union africaine)",
            "date_limite": date_iso(echeance_txt),
            "description": ". ".join(
                part for part in (
                    type_avis,
                    f"Référence {reference}",
                    "Vérifier dans l'avis les pays et profils de fournisseurs admissibles",
                ) if part
            ),
            "lien": href,
        })
    return items


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list[dict]:
    """Collecte les avis actuellement listés par les deux portails officiels."""
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)
    nouveaux = []
    vus = set()

    for url in (AFRICACDC_APPM_URL, AFRICACDC_SUPPLY_URL):
        try:
            html = get_html(url, HEADERS, timeout=40)
        except Exception as exc:
            print(f"Africa CDC : page inaccessible ({str(exc)[:70]}).")
            continue

        for item in lire_tableau(html, url):
            if item["id"] in seen_ids or item["id"] in vus:
                continue
            vus.add(item["id"])
            nouveaux.append(item)
            if limite is not None and len(nouveaux) >= limite:
                return nouveaux
    return nouveaux


class AfricaCdcScraper(BaseScraper):
    source_key = "africacdc"
    nom = "Africa CDC (marchés santé)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
