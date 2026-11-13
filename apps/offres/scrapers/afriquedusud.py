"""Marches publics d'Afrique du Sud (eTenders, National Treasury).

Source : GET https://www.etenders.gov.za/Home/PaginatedTenderOpportunities
         ?status=1&start=<n>&length=<m>   (JSON, protocole DataTables)

Constate le 14/09/2026 :

  - status=1 rend les avis publies et ouverts ; la reponse porte
    recordsTotal (2 247 au sondage) et `data`, une ligne par avis avec une
    cinquantaine de champs. Ceux qu'on lit : id, tender_No, description,
    category, type, organ_of_State, province, date_Published, closing_Date
    et supportDocument (les pieces jointes).

  - Le tri par defaut du portail est la date de publication decroissante
    (colonne 2) ; on le demande explicitement pour que l'arret sur page
    connue reste valable.

  - Il n'y a pas de page de fiche : le portail deplie le detail dans le
    tableau. Le lien conserve est celui de la premiere piece jointe (l'avis
    lui-meme, presque toujours un PDF), et sinon la page des opportunites.

  - Les dates sont en ISO avec heure ("2026-10-16T12:00:00").

LICENCE : le Tresor national autorise tout usage, commercial compris, et la
republication a condition de garder un lien vers la source. Voir config.py.
"""

import re
import time
from datetime import date
from urllib.parse import quote

from .base import BaseScraper
from .http import get_json
from Offre.sources import (ZA_LISTE, ZA_PAGE, ZA_DOCUMENT, ZA_PAGE_SIZE,
                    ZA_PAGE_DELAY, ZA_MAX_PAGES, FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "application/json",
           "X-Requested-With": "XMLHttpRequest"}


def texte_brut(valeur) -> str:
    return re.sub(r"\s+", " ", str(valeur or "")).strip()


def date_iso(brut: str) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", brut or "")
    if not m:
        return ""
    try:
        return date(*(int(x) for x in m.groups())).isoformat()
    except ValueError:
        return ""


def lien_du_document(avis: dict) -> str:
    """URL de telechargement de la premiere piece jointe active, ou vide.

    Le portail compose le lien avec l'identifiant du blob et le nom de
    fichier ; on reproduit exactement sa construction.
    """
    for doc in avis.get("supportDocument") or []:
        if doc.get("active") is False or not doc.get("supportDocumentID"):
            continue
        blob = doc["supportDocumentID"] + (doc.get("extension") or "")
        return (f"{ZA_DOCUMENT}?blobName={quote(blob)}"
                f"&downloadedFileName={quote(doc.get('fileName') or blob)}")
    return ""


def normalize(avis: dict) -> dict:
    description = texte_brut(avis.get("description"))
    details = []
    for cle, libelle in (("type", ""), ("category", "Category"),
                         ("province", "Province")):
        valeur = texte_brut(avis.get(cle))
        if valeur and valeur.upper() != "N/A":
            details.append(f"{libelle} {valeur}".strip())
    if texte_brut(avis.get("tender_No")):
        details.append(f"Tender {texte_brut(avis['tender_No'])}")
    if avis.get("briefingCompulsory"):
        details.append("Compulsory briefing session")

    return {
        "id": f"za-{avis['id']}",
        "source": "afriquedusud",
        "titre": description or texte_brut(avis.get("tender_No")) or "Tender",
        "organisation": texte_brut(avis.get("organ_of_State") or avis.get("department")),
        "pays": "Afrique du Sud",
        "date_limite": date_iso(avis.get("closing_Date")),
        "date_publication": date_iso(avis.get("date_Published")),
        "description": ". ".join(details + [description]) if details else description,
        "lien": lien_du_document(avis) or ZA_PAGE,
    }


def page_json(start: int, longueur: int) -> list:
    """Une page du tableau, triee par publication decroissante."""
    params = {"draw": 1, "start": start, "length": longueur, "status": 1,
              "order[0][column]": 2, "order[0][dir]": "desc", "search[value]": ""}
    reponse = get_json(ZA_LISTE, HEADERS, params=params, timeout=90)
    return reponse.get("data") or []


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Parcourt les pages jusqu'a une page entierement connue."""
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)
    aujourd_hui = date.today().isoformat()

    for page in range(ZA_MAX_PAGES):
        if page > 0 and ZA_PAGE_DELAY:
            time.sleep(ZA_PAGE_DELAY)
        try:
            bruts = page_json(page * ZA_PAGE_SIZE, ZA_PAGE_SIZE)
        except Exception as exc:
            print(f"Afrique du Sud : page {page} inaccessible ({str(exc)[:70]}).")
            print(f"  {len(nouveaux)} avis deja collecte(s) sont conserves.")
            return nouveaux

        if not bruts:
            if page == 0:
                print("Afrique du Sud : reponse vide, le protocole a peut-etre change.")
            break

        inconnus_page = 0
        for brut in bruts:
            if not brut.get("id"):
                continue
            item = normalize(brut)
            if item["id"] in seen_ids or item["id"] in vus_ce_run:
                continue
            vus_ce_run.add(item["id"])
            inconnus_page += 1
            # status=1 ne devrait rendre que des avis ouverts ; on le verifie
            # quand meme, une echeance passee ne merite pas le tri.
            if item["date_limite"] and item["date_limite"] < aujourd_hui:
                continue
            nouveaux.append(item)
            if limite is not None and len(nouveaux) >= limite:
                print(f"Afrique du Sud : plafond premier lancement atteint ({limite} avis).")
                return nouveaux

        if not complet and inconnus_page == 0:
            break
        if len(bruts) < ZA_PAGE_SIZE:
            break

    return nouveaux


class AfriqueDuSudScraper(BaseScraper):
    source_key = "afriquedusud"
    nom = "Afrique du Sud (eTenders)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
