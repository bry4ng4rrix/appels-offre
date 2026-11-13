"""Marches publics du Malawi (PPDA, Procurement Notices).

Source : https://www.ppda.mw/tenders

Constate le 14/09/2026 :

  - Un tableau id="tenderstable" de six colonnes -- titre, institution,
    reference, date de publication, date de cloture, piece jointe -- sans
    pagination, qui ne liste que les avis en cours. Une requete suffit.

  - Les dates sont en ISO (AAAA-MM-JJ) : pas de conversion.

  - Le portail n'expose aucun identifiant technique, et une reference sur
    vingt-neuf est partagee par deux avis (deux lots d'un meme dossier).
    L'identifiant hache donc reference, titre et date de cloture.

  - Le titre est parfois un simple libelle de lot ("MEDICAL EQUIPMENT1")
    alors que le nom du PDF joint decrit le marche. Il est repris dans la
    description, sans son extension.
"""

import hashlib
import os
import re
from datetime import date
from urllib.parse import unquote

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import MW_URL, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "text/html"}

TITRE, INSTITUTION, REFERENCE, PUBLICATION, CLOTURE, PIECE = 0, 1, 2, 3, 4, 5


def texte_brut(cellule) -> str:
    return re.sub(r"\s+", " ", cellule.get_text(" ", strip=True)).strip()


def date_iso(brut: str) -> str:
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", brut or "")
    if not m:
        return ""
    try:
        return date(*(int(x) for x in m.groups())).isoformat()
    except ValueError:
        return ""


def identifiant(reference: str, titre: str, cloture: str) -> str:
    graine = f"{reference}|{titre}|{cloture}".encode("utf-8")
    return "mw-" + hashlib.sha1(graine).hexdigest()[:12]


def nom_de_la_piece(lien: str) -> str:
    """"…/RFQ Health - Supply of CSSD.pdf" -> "RFQ Health - Supply of CSSD"."""
    nom = unquote(os.path.basename(lien or ""))
    return re.sub(r"\s+", " ", os.path.splitext(nom)[0]).strip()


def lignes_du_tableau(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="tenderstable")
    if table is None:
        return []
    return [tr.find_all("td") for tr in table.find_all("tr")
            if len(tr.find_all("td")) >= 6]


def normalize(cellules: list) -> dict:
    titre = texte_brut(cellules[TITRE])
    reference = texte_brut(cellules[REFERENCE])
    cloture = date_iso(texte_brut(cellules[CLOTURE]))
    a = cellules[PIECE].find("a", href=True)
    lien = a["href"].strip() if a else ""
    piece = nom_de_la_piece(lien)

    details = []
    if reference:
        details.append(f"Reference {reference}")
    if piece and piece.upper() != titre.upper():
        details.append(piece)

    return {
        "id": identifiant(reference, titre, cloture),
        "source": "malawi",
        "titre": titre,
        "organisation": texte_brut(cellules[INSTITUTION]),
        "pays": "Malawi",
        "date_limite": cloture,
        "date_publication": date_iso(texte_brut(cellules[PUBLICATION])),
        "description": ". ".join(details + [titre]),
        "lien": lien or MW_URL,
    }


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Collecte les avis inconnus et encore ouverts. `complet` ne change rien :
    la page n'a ni pagination ni archive."""
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)
    aujourd_hui = date.today().isoformat()

    try:
        html = get_html(MW_URL, HEADERS, timeout=60)
    except Exception as exc:
        print(f"Malawi : page inaccessible ({str(exc)[:70]}).")
        return []

    lignes = lignes_du_tableau(html)
    if not lignes:
        print("Malawi : aucun avis reconnu, la mise en page a peut-etre change.")
        return []

    for cellules in lignes:
        item = normalize(cellules)
        if not item["titre"] or item["id"] in seen_ids or item["id"] in vus_ce_run:
            continue
        vus_ce_run.add(item["id"])
        if item["date_limite"] and item["date_limite"] < aujourd_hui:
            continue
        nouveaux.append(item)
        if limite is not None and len(nouveaux) >= limite:
            print(f"Malawi : plafond premier lancement atteint ({limite} avis).")
            break

    return nouveaux


class MalawiScraper(BaseScraper):
    source_key = "malawi"
    nom = "Malawi (PPDA)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
