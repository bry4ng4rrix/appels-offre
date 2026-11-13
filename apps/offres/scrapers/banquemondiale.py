"""Projets de la Banque mondiale via l'API de recherche publique.

Source : https://projects.banquemondiale.org — le site s'appuie sur
https://search.worldbank.org/api/v3/projects, qui est ouverte et sans cle.
On interroge donc l'API plutot que de scraper le HTML.

Les projets sont tries par date d'approbation decroissante, ce qui permet la
meme logique incrementale que les autres sources : on s'arrete des qu'un projet
deja connu apparait.
"""

from .base import BaseScraper
from .http import get_json
from Offre.sources import (
    BM_BASE_URL,
    BM_DETAIL_URL,
    BM_PAYS,
    BM_PAGE_SIZE,
    BM_MAX_PAGES,
    FIRST_RUN_MAX_ITEMS,
)

HEADERS = {"User-Agent": "veille-appels/1.0"}

# Jeu de champs verifie contre l'API : demander en plus url, sector ou theme
# fait repondre 500, alors que chacun passe isolement.
CHAMPS = (
    "id,project_name,countryshortname,regionname,"
    "boardapprovaldate,closingdate,status,impagency,borrower,project_abstract"
)


def fetch_page(pays: str, offset: int) -> list:
    """Une page de projets, du plus recemment approuve au plus ancien."""
    params = {
        "format": "json",
        "rows": BM_PAGE_SIZE,
        "os": offset,
        "fl": CHAMPS,
        "srt": "boardapprovaldate",
        "order": "desc",
    }
    if pays:
        params["countrycode_exact"] = pays

    # L'API renvoie un dict {id: projet} dont l'ordre suit le tri demande.
    return list(get_json(BM_BASE_URL, HEADERS, params).get("projects", {}).values())


def normalize(projet: dict) -> dict:
    """Ramene un projet au format commun aux trois sources."""
    pid = projet.get("id") or projet.get("proj_id") or ""

    # impagency (agence d'execution) est plus parlant que borrower, qui est
    # presque toujours le ministere des finances.
    organisation = projet.get("impagency") or projet.get("borrower") or ""

    return {
        "id": pid,
        "source": "banquemondiale",
        "titre": projet.get("project_name", ""),
        "organisation": organisation,
        "pays": projet.get("countryshortname") or projet.get("regionname", ""),
        # Date de fin du projet, pas une date limite de candidature : un projet
        # de la Banque mondiale n'a pas d'echeance de depot. Verifie : aucun des
        # 284 projets malgaches ne cloture sous 14 jours, donc cela ne declenche
        # pas de fausse urgence dans le rapport.
        "date_limite": (projet.get("closingdate") or "")[:10],
        # project_abstract vient dans la meme requete : aucun cout supplementaire.
        "description": (projet.get("project_abstract") or "").strip(),
        "lien": BM_DETAIL_URL.format(id=pid),
    }


def scrape_new_projects(seen_ids: set, complet: bool = False) -> list:
    """Parcourt les projets, meme logique incrementale que les autres sources."""
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    # L'API refuse plusieurs codes pays dans une meme requete : on boucle.
    for pays in (BM_PAYS or [""]):
        for page in range(BM_MAX_PAGES):
            bruts = fetch_page(pays, page * BM_PAGE_SIZE)
            if not bruts:
                break

            arret_pays = False
            for brut in bruts:
                item = normalize(brut)
                if not item["id"]:
                    continue
                if item["id"] in seen_ids:
                    if complet:
                        continue
                    arret_pays = True
                    break
                if item["id"] in vus_ce_run:
                    continue
                vus_ce_run.add(item["id"])
                nouveaux.append(item)
                if limite is not None and len(nouveaux) >= limite:
                    print(f"Banque mondiale : plafond premier lancement atteint "
                          f"({limite} projets).")
                    return nouveaux

            if arret_pays:
                break

    return nouveaux


class BanqueMondialeScraper(BaseScraper):
    source_key = "banquemondiale"
    nom = "Banque mondiale (projets)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_projects(seen_ids, complet=complet)
