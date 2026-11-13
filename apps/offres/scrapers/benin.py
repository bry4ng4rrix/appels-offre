"""Marches publics du Benin (SIGMAP, via l'API du portail).

Source : GET https://api.marches-publics.bj/v2/api/portail/appelsoffres
         ?status=1&page=<n>&size=<m>&search=

Constate le 14/09/2026 :

  - status=1 rend les avis d'appel a concurrence en cours : 52 au sondage,
    en une page de 100. La reponse est une page Spring : `content`,
    `totalElements`, `last`.

  - Chaque entree est un dossier (dosID) qui enveloppe l'appel d'offres
    (appelsoffres.apoObjet, apoReference, typemarche.libelle) et l'autorite
    contractante (autoriteContractante.denomination). Les dates sont en
    ISO : dosDatePublication, dosDateLimiteDepot. dosFichier est le PDF de
    l'avis ; `expired` dit si l'echeance est passee.

  - La fiche du portail est /appels-doffres/<dosID>.
"""

import re
from datetime import date

from .base import BaseScraper
from .http import get_json
from Offre.sources import BJ_API, BJ_FICHE, BJ_PAGE_SIZE, BJ_MAX_PAGES, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "application/json",
           "Origin": "https://marches-publics.bj",
           "Referer": "https://marches-publics.bj/"}


def texte_brut(valeur) -> str:
    return re.sub(r"\s+", " ", str(valeur or "")).strip()


def date_iso(brut) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(brut or ""))
    if not m:
        return ""
    try:
        return date(*(int(x) for x in m.groups())).isoformat()
    except ValueError:
        return ""


def normalize(dossier: dict) -> dict:
    appel = dossier.get("appelsoffres") or {}
    autorite = dossier.get("autoriteContractante") or {}
    objet = texte_brut(appel.get("apoObjet"))
    reference = texte_brut(dossier.get("dosReference") or appel.get("apoReference"))
    type_marche = texte_brut((appel.get("typemarche") or {}).get("libelle"))

    details = [x for x in (type_marche,) if x]
    if reference:
        details.append(f"Reference {reference}")
    lots = dossier.get("dosNombreLots")
    if isinstance(lots, int) and lots > 1:
        details.append(f"{lots} lots")

    return {
        "id": f"bj-{dossier['dosID']}",
        "source": "benin",
        "titre": objet or (f"Avis {reference}" if reference else "Avis Benin"),
        "organisation": texte_brut(autorite.get("denomination")),
        "pays": "Bénin",
        "date_limite": date_iso(dossier.get("dosDateLimiteDepot")),
        "date_publication": date_iso(dossier.get("dosDatePublication") or dossier.get("dosDateCreation")),
        "description": ". ".join(details + [objet]) if details else objet,
        "lien": f"{BJ_FICHE}{dossier['dosID']}",
    }


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Lit les avis en cours, page par page. La liste ne contenant que des
    avis ouverts, `complet` ne change que le plafond."""
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    for page in range(BJ_MAX_PAGES):
        try:
            reponse = get_json(BJ_API, HEADERS, timeout=60,
                               params={"page": page, "size": BJ_PAGE_SIZE,
                                       "search": "", "status": "1"})
        except Exception as exc:
            print(f"Benin : page {page} inaccessible ({str(exc)[:70]}).")
            return nouveaux

        dossiers = reponse.get("content") or []
        if not dossiers:
            if page == 0:
                print("Benin : reponse vide, l'API a peut-etre change.")
            break

        for dossier in dossiers:
            if not dossier.get("dosID"):
                continue
            item = normalize(dossier)
            if item["id"] in seen_ids or item["id"] in vus_ce_run:
                continue
            vus_ce_run.add(item["id"])
            if dossier.get("expired"):
                continue
            nouveaux.append(item)
            if limite is not None and len(nouveaux) >= limite:
                print(f"Benin : plafond premier lancement atteint ({limite} avis).")
                return nouveaux

        if reponse.get("last") or len(dossiers) < BJ_PAGE_SIZE:
            break

    return nouveaux


class BeninScraper(BaseScraper):
    source_key = "benin"
    nom = "Benin (SIGMAP)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
