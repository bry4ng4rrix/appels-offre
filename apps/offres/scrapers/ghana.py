"""Marches publics du Ghana (GHANEPS).

Source : https://www.ghaneps.gov.gh/epps/quickSearchAction.do?searchSelect=6

Plateforme e-PPS de la Public Procurement Authority. Constate le 14/09/2026 :

  - "Current Tenders" liste les avis en phase de depot dans un tableau
    id="T01" de neuf colonnes : numero, titre (lien vers la fiche), entite,
    icone d'information, echeance de depot, procedure, statut, PDF de
    l'avis, date de publication. Dix lignes par page, 72 avis au sondage.

  - Les dates de la liste sont au format Java par defaut, "Mon Sep 28
    10:00:00 GMT 2026". La fiche les donne en JJ/MM/AAAA ; on lit celles de
    la liste, qui suffisent, et la fiche pour la description.

  - La fiche est une liste de definitions <dt>/<dd>. On y prend la
    description, le type (Goods / Works / Services), la methode et le code
    UNSPSC, qui disent au tri de quoi il s'agit bien mieux que le titre en
    capitales.

  - resourceId, present dans le lien de la fiche, est l'identifiant.

ELIGIBILITE : les 72 avis du sondage relevent du "National Competitive
Tendering" ou de selections de consultants. La methode est reprise dans la
description pour que le tri en tienne compte.
"""

import re
import time
from datetime import date

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import (GH_LISTE, GH_DETAIL, GH_PARAM_PAGE, GH_PAGE_DELAY,
                    GH_MAX_PAGES, FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "text/html"}

MOIS_EN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

#: Colonnes du tableau T01.
TITRE, ENTITE, ECHEANCE, PROCEDURE, STATUT, PUBLICATION = 1, 2, 4, 5, 6, 8

#: Champs de la fiche repris dans la description, avec leur libelle.
CHAMPS_FICHE = [("Description", ""), ("Procurement Type", "Type"),
                ("Procurement Method", "Method"), ("UNSPSC Codes", "UNSPSC")]

RESOURCE_ID = re.compile(r"resourceId=(\d+)")


def texte_brut(cellule) -> str:
    return re.sub(r"\s+", " ", cellule.get_text(" ", strip=True)).strip()


def date_iso(brut: str) -> str:
    """"Mon Sep 28 10:00:00 GMT 2026" -> "2026-09-28". Vide si illisible."""
    m = re.search(r"\b([A-Za-z]{3})\s+(\d{1,2})\s+[\d:]+\s+\w+\s+(\d{4})", brut or "")
    if not m:
        return ""
    mois = MOIS_EN.get(m.group(1).lower())
    if not mois:
        return ""
    try:
        return date(int(m.group(3)), mois, int(m.group(2))).isoformat()
    except ValueError:
        return ""


def lignes_du_tableau(html: str) -> list:
    """Lignes de donnees du tableau T01, en-tete exclue. [] si absent."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="T01")
    if table is None:
        return []
    return [tr.find_all("td") for tr in table.find_all("tr")
            if len(tr.find_all("td")) >= 9]


def champs_de_la_fiche(html: str) -> dict:
    """Lit la liste de definitions <dt>libelle :</dt><dd>valeur</dd> de la fiche.

    On indexe sur le libelle sans ses deux-points. texte_brut ramene deja
    l'espace insecable de "Bid Security Amount&nbsp;(GHS):" a un espace.
    """
    soup = BeautifulSoup(html, "html.parser")
    champs = {}
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd is None:
            continue
        libelle = texte_brut(dt).rstrip(":").strip()
        champs[libelle] = texte_brut(dd)
    return champs


def fiche(resource_id: str) -> dict:
    try:
        html = get_html(GH_DETAIL, HEADERS, params={"resourceId": resource_id}, timeout=60)
    except Exception as exc:
        print(f"  Ghana : fiche {resource_id} inaccessible ({str(exc)[:60]}).")
        return {}
    return champs_de_la_fiche(html)


def normalize(cellules: list, champs: dict) -> dict:
    lien = cellules[TITRE].find("a", href=True)
    m = RESOURCE_ID.search(lien["href"]) if lien else None
    resource_id = m.group(1) if m else ""
    titre = texte_brut(cellules[TITRE])

    details = []
    description = champs.get("Description", "")
    if description and description.strip().upper() != titre.upper():
        details.append(description)
    for cle, libelle in CHAMPS_FICHE[1:]:
        if champs.get(cle):
            details.append(f"{libelle} {champs[cle]}")
    procedure = texte_brut(cellules[PROCEDURE])
    if procedure and not champs.get("Procurement Method"):
        details.append(f"Method {procedure}")

    return {
        "id": f"gh-{resource_id}",
        "source": "ghana",
        "titre": titre,
        "organisation": texte_brut(cellules[ENTITE]),
        "pays": "Ghana",
        "date_limite": date_iso(texte_brut(cellules[ECHEANCE])),
        "date_publication": date_iso(texte_brut(cellules[PUBLICATION])),
        "description": ". ".join(details) if details else titre,
        "lien": f"{GH_DETAIL}?resourceId={resource_id}" if resource_id else GH_LISTE,
    }


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Parcourt les pages des avis en cours jusqu'a une page connue.

    La liste ne contient que des avis en phase de depot : pas d'avis clos a
    ecarter, et une page entierement connue signifie que la suite l'est
    aussi, la liste etant triee par publication decroissante.
    """
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    for page in range(1, GH_MAX_PAGES + 1):
        if page > 1 and GH_PAGE_DELAY:
            time.sleep(GH_PAGE_DELAY)
        try:
            html = get_html(GH_LISTE, HEADERS,
                            params={"searchSelect": 6, GH_PARAM_PAGE: page}, timeout=60)
        except Exception as exc:
            print(f"Ghana : page {page} inaccessible ({str(exc)[:70]}).")
            break

        lignes = lignes_du_tableau(html)
        if not lignes:
            if page == 1:
                print("Ghana : aucun avis reconnu, la mise en page a peut-etre change.")
            break

        inconnus_page = 0
        for cellules in lignes:
            lien = cellules[TITRE].find("a", href=True)
            m = RESOURCE_ID.search(lien["href"]) if lien else None
            if not m:
                continue
            ident = f"gh-{m.group(1)}"
            if ident in seen_ids or ident in vus_ce_run:
                continue
            vus_ce_run.add(ident)
            inconnus_page += 1

            time.sleep(GH_PAGE_DELAY)
            nouveaux.append(normalize(cellules, fiche(m.group(1))))
            if limite is not None and len(nouveaux) >= limite:
                print(f"Ghana : plafond premier lancement atteint ({limite} avis).")
                return nouveaux

        if not complet and inconnus_page == 0:
            break
        # Une derniere page incomplete signale la fin : inutile d'en demander
        # une de plus, qui repeterait la derniere.
        if len(lignes) < 10:
            break

    return nouveaux


class GhanaScraper(BaseScraper):
    source_key = "ghana"
    nom = "Ghana (GHANEPS)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
