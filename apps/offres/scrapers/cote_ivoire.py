"""Appels d'offres de Cote d'Ivoire (DGMP, Direction generale des marches publics).

Source : https://www.marchespublics.ci/appel_offre, une seule page HTML avec
tout l'historique. Colonnes : numero, type de marche, objet, autorite
contractante, publication, date limite ; les dates portent leur forme ISO
dans data-order. Aucune fiche par avis : le lien renvoie a la liste.
"""

from datetime import date

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import CI_URL, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0"}


def texte(el) -> str:
    return " ".join(el.get_text(" ").split()) if el else ""


def normalize(ligne) -> dict | None:
    cellules = ligne.find_all("td", recursive=False)
    if len(cellules) < 6:
        return None
    numero, genre, objet, autorite = (texte(c) for c in cellules[:4])
    if not numero or not objet:
        return None
    return {
        "id": f"ci-{numero.replace(' ', '')}",
        "source": "cote_ivoire",
        "titre": objet,
        "organisation": autorite,
        "pays": "Côte d'Ivoire",
        "date_limite": cellules[5].get("data-order", ""),
        "date_publication": cellules[4].get("data-order", ""),
        "description": f"{genre}. Ref {numero}. {objet}",
        "lien": CI_URL,
    }


def extraire(html: str) -> list:
    soupe = BeautifulSoup(html, "html.parser")
    return [i for i in map(normalize, soupe.select("tbody tr")) if i]


class CoteIvoireScraper(BaseScraper):
    source_key = "cote_ivoire"
    nom = "Côte d'Ivoire (DGMP)"
    site = CI_URL

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        nouveaux = [i for i in extraire(get_html(CI_URL, HEADERS, timeout=60))
                    if i["id"] not in seen_ids and i["date_limite"] >= aujourdhui]
        return nouveaux[:limite] if limite else nouveaux
