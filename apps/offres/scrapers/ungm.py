"""Avis de marches de l'ONU publies sur UNGM (United Nations Global Marketplace).

Source : https://www.ungm.org/Public/Notice -- cadre juridique et choix
techniques dans Offre/sources.py.

Deroulement :
  1. GET de la page publique : cookie de session + jeton anti-forgery.
  2. POST /Public/Notice/Search, page apres page (15 avis), avis actifs tries
     par date de publication decroissante. Chaque ligne donne l'identifiant,
     le titre, l'echeance, la publication, l'agence, le type, la reference et
     le pays. En incremental, on s'arrete a la premiere page sans nouveaute.
  3. Pour chaque avis nouveau : la fiche (description, pays beneficiaires,
     niveau d'enregistrement, pieces jointes) et l'onglet des codes UNSPSC.
     Une fiche illisible n'ecarte pas l'avis : il garde les donnees de la liste.

Les pieces jointes ne sont pas telechargees -- les conditions d'UNGM
interdisent de les stocker -- seuls leur nom et leur lien sont repris.
"""

import re
import time
from datetime import datetime

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html, post_html
from Offre.sources import (FIRST_RUN_MAX_ITEMS, UNGM_BASE, UNGM_MAX_PAGES,
                           UNGM_PAGE_DELAY, UNGM_PAGE_SIZE, UNGM_RECHERCHE,
                           UNGM_TIMEOUT, UNGM_URL)

HEADERS = {"User-Agent": "veille-appels/1.0"}


def texte(el) -> str:
    return " ".join(el.get_text(" ").split()) if el else ""


def date_ungm(brut: str) -> str:
    """"24-Nov-2026 10:00 (GMT 1.00)" -> "2026-11-24" ; illisible -> ""."""
    m = re.search(r"\d{1,2}-[A-Za-z]{3}-\d{4}", brut or "")
    try:
        return datetime.strptime(m.group(), "%d-%b-%Y").date().isoformat() if m else ""
    except ValueError:
        return ""


def jeton(html: str) -> str:
    m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', html)
    if not m:
        raise ValueError("jeton anti-forgery absent de la page UNGM")
    return m.group(1)


def freine(exc) -> bool:
    """429 encore la apres les reprises de http.py : insister aggraverait."""
    return getattr(getattr(exc, "response", None), "status_code", None) == 429


def criteres(page: int) -> dict:
    """Corps de la recherche, tel que l'envoie le script de la page."""
    return {"PageIndex": page, "PageSize": UNGM_PAGE_SIZE, "Title": "", "Description": "",
            "Reference": "", "PublishedFrom": "", "PublishedTo": "", "DeadlineFrom": "",
            "DeadlineTo": "", "Countries": [], "Agencies": [], "UNSPSCs": [],
            "NoticeTypes": [], "SortField": "DatePublished", "SortAscending": False,
            "isPicker": False, "IsSustainable": False, "IsActive": True,
            "NoticeDisplayType": None, "NoticeSearchTotalLabelId": "noticeSearchTotal",
            "TypeOfCompetitions": []}


def normalize(ligne) -> dict | None:
    """Ligne div.dataRow -> ScrapedItem ; None si elle n'a pas la forme attendue."""
    cellules = ligne.select(":scope > div[role=cell]")
    notice_id = ligne.get("data-noticeid", "")
    titre = texte(ligne.select_one(".resultTitle .ungm-title"))
    if len(cellules) < 8 or not notice_id.isdigit() or not titre:
        return None
    echeance = cellules[2].find("span")
    publie, agence, nature, ref, pays = (texte(c) for c in cellules[3:8])
    return {
        "id": f"ungm-{notice_id}",
        "source": "ungm",
        "titre": titre,
        "organisation": agence,
        "pays": pays,
        "date_publication": date_ungm(publie),
        "date_limite": date_ungm(texte(echeance)),
        "description": ". ".join(x for x in (nature, f"Reference {ref}" if ref else "") if x),
        "lien": f"{UNGM_URL}/{notice_id}",
    }


def extraire(html: str) -> tuple[list, int]:
    """Page de resultats -> (avis lisibles, nombre de lignes de la page)."""
    lignes = BeautifulSoup(html, "html.parser").select("div.dataRow[data-noticeid]")
    return [i for i in map(normalize, lignes) if i], len(lignes)


def lire_fiche(html: str) -> dict:
    """Fiche /Public/Notice/<id> -> champs "libelle: valeur", description, documents."""
    soupe = BeautifulSoup(html, "html.parser")
    champs = {texte(r.select_one(".label")).rstrip(":"): texte(r.select_one(".value"))
              for r in soupe.select("div.row") if r.select_one(".label")}
    description = ""
    for bloc in soupe.select("div.ungm-list-item"):
        if texte(bloc.select_one(":scope > .title")) == "Description":
            corps = bloc.select_one(":scope > div:not(.title)")
            description = corps.get_text("\n").strip() if corps else ""
    documents = [(texte(a), UNGM_BASE + a["href"])
                 for a in soupe.select(".docslist a.lnkShowDocument[href]")]
    return {"champs": champs, "description": description, "documents": documents}


def lire_unspsc(html: str) -> list[str]:
    """Onglet UNSPSC -> ["78204002 Flight Operations ..."]. Les noeuds "filtered"
    sont les ancetres affiches pour le contexte, pas des codes retenus."""
    codes = []
    for noeud in BeautifulSoup(html, "html.parser").select("span.nodeName"):
        if "filtered" in noeud.get("class", []):
            continue
        parties = [texte(s) for s in noeud.select(":scope > span")]
        codes.append(f"{parties[0]} {parties[-1]}" if len(parties) >= 3 else texte(noeud))
    return codes


def completer(item: dict, fiche: dict, codes: list) -> None:
    """Ajoute a la description ce que seule la fiche porte."""
    champs = fiche["champs"]
    en_tete = [item["description"]]
    for libelle in ("Beneficiary countries or territories", "Registration level"):
        if champs.get(libelle):
            en_tete.append(f"{libelle} : {champs[libelle]}")
    if codes:
        en_tete.append("UNSPSC : " + " ; ".join(codes))
    if fiche["documents"]:
        en_tete.append("Documents : " + " ; ".join(f"{nom} <{url}>" for nom, url in fiche["documents"]))
    item["description"] = ". ".join(x for x in en_tete if x) + (
        "\n\n" + fiche["description"] if fiche["description"] else "")


class UngmScraper(BaseScraper):
    source_key = "ungm"
    nom = "UNGM (Nations unies)"
    site = UNGM_URL

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        entetes = {**HEADERS, "RequestVerificationToken":
                   jeton(get_html(UNGM_URL, HEADERS, timeout=UNGM_TIMEOUT))}
        nouveaux, connus = [], set(seen_ids)
        for page in range(UNGM_MAX_PAGES):
            if page:
                time.sleep(UNGM_PAGE_DELAY)
            try:
                html = post_html(UNGM_RECHERCHE, entetes, criteres(page), timeout=UNGM_TIMEOUT)
            except Exception as exc:
                if not (nouveaux and freine(exc)):
                    raise
                print(f"  UNGM : limite de debit page {page}, on garde les {len(nouveaux)} avis lus")
                break
            items, nb_lignes = extraire(html)
            frais = [i for i in items if i["id"] not in connus]
            connus.update(i["id"] for i in frais)
            nouveaux += frais
            if nb_lignes - len(items):
                print(f"  UNGM : {nb_lignes - len(items)} ligne(s) illisible(s) page {page}")
            # Tri par publication decroissante : une page sans nouveaute = la suite est connue.
            if (nb_lignes < UNGM_PAGE_SIZE or (not frais and not complet)
                    or (limite and len(nouveaux) >= limite)):
                break
        nouveaux = nouveaux[:limite] if limite else nouveaux

        echecs = 0
        for item in nouveaux:
            numero = item["id"].removeprefix("ungm-")
            try:
                time.sleep(UNGM_PAGE_DELAY)
                fiche = lire_fiche(get_html(item["lien"], HEADERS, timeout=UNGM_TIMEOUT))
                time.sleep(UNGM_PAGE_DELAY)
                codes = lire_unspsc(get_html(f"{UNGM_URL}/Unspscs/{numero}", HEADERS,
                                             timeout=UNGM_TIMEOUT))
                completer(item, fiche, codes)
            except Exception as exc:
                echecs += 1
                print(f"  UNGM : fiche {numero} illisible ({str(exc)[:80]}), donnees de la liste gardees")
                if freine(exc):
                    print("  UNGM : limite de debit, fiches restantes non lues")
                    break
        print(f"  UNGM : {len(nouveaux)} nouveau(x) avis, {echecs} fiche(s) en echec")
        return nouveaux
