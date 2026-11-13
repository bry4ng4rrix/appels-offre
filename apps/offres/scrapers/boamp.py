"""Marches publics francais de l'ocean Indien (BOAMP).

Source : https://boamp-datadila.opendatasoft.com/api/explore/v2.1/...

Bulletin officiel des annonces des marches publics. API Opendatasoft ouverte,
sans authentification, 1 699 819 avis au total.

Le filtre porte sur les departements de l'ocean Indien -- La Reunion (974) et
Mayotte (976) -- soit un marche francophone geographiquement proche
d'Antananarivo, et dont les prestations numeriques sont realisables a distance.

Volumes constates le 24/08/2026 :
    La Reunion   21 483 avis, dont 143 encore ouverts
    Mayotte       8 047 avis

RESERVE JURIDIQUE : le jeu de donnees n'expose pas de champ `license` dans ses
metadonnees. Le BOAMP relevant de l'open data administratif francais, la
Licence Ouverte s'applique vraisemblablement, mais cela n'a PAS ete verifie
sur une source faisant foi. A confirmer avant toute rediffusion.
"""

from datetime import date

from .base import BaseScraper
from .http import get_json
from Offre.sources import (
    BOAMP_API_URL,
    BOAMP_DEPARTEMENTS,
    BOAMP_PAGE_SIZE,
    BOAMP_MAX_PAGES,
    FIRST_RUN_MAX_ITEMS,
)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "application/json"}

#: Le champ `code_departement` est un tableau : "974" y figure comme element.
DEPARTEMENTS = {
    "974": "La Réunion (France)",
    "976": "Mayotte (France)",
    "975": "Saint-Pierre-et-Miquelon",
}


def libelle_departement(codes) -> str:
    """Nom lisible du departement, pour que le tri situe l'offre.

    Un code brut ("974") ne dit rien au modele : le prompt raisonne sur des
    lieux nommes. On renvoie donc "La Reunion (France)".
    """
    if isinstance(codes, str):
        codes = [codes]
    for code in (codes or []):
        if code in DEPARTEMENTS:
            return DEPARTEMENTS[code]
    return ", ".join(codes or []) or ""


def premiere_valeur(valeur) -> str:
    """Plusieurs champs arrivent en tableau a un seul element."""
    if isinstance(valeur, list):
        return str(valeur[0]) if valeur else ""
    return str(valeur or "")


def normalize(brut: dict) -> dict:
    """Ramene un avis au format commun aux autres sources."""
    idweb = brut.get("idweb") or brut.get("id") or ""
    echeance = (brut.get("datelimitereponse") or "")[:10]

    details = []
    if brut.get("dateparution"):
        details.append(f"Paru le {brut['dateparution']}")
    for champ in ("nature_libelle", "procedure_libelle", "famille_libelle"):
        if brut.get(champ):
            details.append(premiere_valeur(brut[champ]))
    descripteurs = brut.get("descripteur_libelle")
    if descripteurs:
        liste = descripteurs if isinstance(descripteurs, list) else [descripteurs]
        details.append("Mots-cles : " + ", ".join(str(d) for d in liste[:6]))

    return {
        "id": f"boamp-{idweb}" if idweb else "",
        "source": "boamp",
        "titre": brut.get("objet") or f"Avis BOAMP {idweb}",
        "organisation": brut.get("nomacheteur") or "",
        "pays": libelle_departement(brut.get("code_departement")),
        "date_limite": echeance,
        "description": ". ".join(d for d in details if d),
        "lien": brut.get("url_avis") or f"https://www.boamp.fr/avis/detail/{idweb}",
    }


def fetch_page(departement: str, offset: int) -> list:
    """Une page d'avis encore ouverts pour un departement.

    `datelimitereponse>now()` est evalue par l'API : inutile de filtrer les
    avis clos apres coup, contrairement au FID ou a la BAD.
    """
    reponse = get_json(f"{BOAMP_API_URL}/records", HEADERS, {
        "where": f'code_departement="{departement}" AND datelimitereponse>now()',
        "limit": BOAMP_PAGE_SIZE,
        "offset": offset,
        "order_by": "datelimitereponse ASC",
    })
    return reponse.get("results") or []


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Collecte les avis inconnus encore ouverts, departement par departement."""
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    for departement in (BOAMP_DEPARTEMENTS or ["974"]):
        for page in range(BOAMP_MAX_PAGES):
            try:
                bruts = fetch_page(departement, page * BOAMP_PAGE_SIZE)
            except Exception as exc:
                print(f"BOAMP : departement {departement} page {page} en echec "
                      f"({str(exc)[:60]}).")
                break

            if not bruts:
                break

            neufs_page = 0
            for brut in bruts:
                item = normalize(brut)
                if not item["id"] or item["id"] in seen_ids or item["id"] in vus_ce_run:
                    continue
                vus_ce_run.add(item["id"])
                nouveaux.append(item)
                neufs_page += 1
                if limite is not None and len(nouveaux) >= limite:
                    print(f"BOAMP : plafond premier lancement atteint ({limite} avis).")
                    return nouveaux

            if not complet and neufs_page == 0:
                break

    return nouveaux


class BoampScraper(BaseScraper):
    source_key = "boamp"
    nom = "BOAMP (Reunion, Mayotte)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
