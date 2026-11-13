"""Appels d'offres de la Commission de l'ocean Indien (COI).

Source : https://www.commissionoceanindien.org/wp-json/wp/v2/posts

Organisation intergouvernementale regroupant les Comores, la France (La
Reunion), Madagascar, Maurice et les Seychelles. Elle passe ses propres
marches, finances par l'Union europeenne, l'AFD et la Banque mondiale.

Constate le 24/08/2026 :
  - robots.txt autorise tout ("Disallow:" vide).
  - Le site est sous WordPress et expose son API REST : on l'interroge plutot
    que de scraper /opportunites-et-carrieres/, pour deux raisons.

Premiere raison : la page HTML desaligne titres et liens. Un avis intitule
"Request for Expressions of Interest COI/RECOS/AMI/2026/001" pointe vers
"summary-contract-coi-pssn-ao-2026-005-2". Le defaut vient de la donnee
elle-meme, pas du parsing -- l'API le reproduit. D'ou l'usage de l'ID de
l'article comme identifiant, jamais du slug.

Seconde raison : l'API permet de cibler les categories d'opportunites, la
page melangeant avis en cours et archives.

ATTENTION : les categories annuelles ne cloisonnent PAS. "Opportunites 2025"
renvoie aussi les articles de 2026, les publications portant plusieurs
etiquettes. Le dedoublonnage par ID est donc indispensable.
"""

import re
import time
from datetime import date
from html import unescape

from .base import BaseScraper
from .http import get_json
from Offre.sources import (
    COI_API_URL,
    COI_CATEGORIES,
    COI_PAGE_SIZE,
    COI_PAGE_DELAY,
    COI_MAX_PAGES,
    COI_MAX_JOURS,
    FIRST_RUN_MAX_ITEMS,
)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "application/json"}


def texte_brut(html: str) -> str:
    """Retire balises et entites d'un champ rendu par WordPress."""
    texte = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", unescape(texte)).strip()


def date_publication(brut: dict):
    """Date de publication WordPress, ou None."""
    valeur = (brut.get("date") or "")[:10]
    try:
        return date.fromisoformat(valeur)
    except ValueError:
        return None


def est_recent(publie) -> bool:
    """La COI ne publie pas de date limite dans ses articles.

    La fraicheur est donc le seul critere disponible : au-dela de
    COI_MAX_JOURS, un avis est considere clos. Un article sans date lisible
    est conserve, on ne peut pas affirmer qu'il est clos.
    """
    if publie is None:
        return True
    return (date.today() - publie).days <= COI_MAX_JOURS


def normalize(brut: dict) -> dict:
    """Ramene un avis au format commun aux autres sources."""
    titre = texte_brut((brut.get("title") or {}).get("rendered", ""))
    contenu = texte_brut((brut.get("content") or {}).get("rendered", ""))
    publie = date_publication(brut)

    details = [f"Publié le {publie}" if publie else "Date de publication inconnue",
               "Date limite non précisée : voir l'avis"]

    return {
        # L'ID de l'article, jamais le slug : celui-ci est parfois celui d'un
        # autre avis (voir la docstring du module).
        "id": f"coi-{brut.get('id')}",
        "source": "coi",
        "titre": titre,
        "organisation": "Commission de l'ocean Indien (COI)",
        # Organisation regionale : Madagascar en est membre, et ses marches
        # sont ouverts aux prestataires des cinq Etats membres.
        "pays": "Océan Indien (Madagascar membre)",
        "date_limite": "",
        # Seul repere d'age pour cette source, qui ne publie pas d'echeance.
        "date_publication": publie or "",
        "description": ". ".join(details) + ". " + contenu[:1200],
        "lien": brut.get("link", ""),
    }


def fetch_page(categorie: int, page: int) -> list:
    """Une page d'avis d'une categorie, du plus recent au plus ancien."""
    return get_json(COI_API_URL, HEADERS, {
        "categories": categorie,
        "per_page": COI_PAGE_SIZE,
        "page": page,
        "orderby": "date",
        "order": "desc",
        "_fields": "id,date,link,title,content",
    })


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Collecte les avis inconnus et suffisamment recents."""
    nouveaux = []
    vus_ce_run = set()
    ignores_anciens = 0
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)
    premier_appel = True

    for categorie in COI_CATEGORIES:
        for page in range(1, COI_MAX_PAGES + 1):
            if not premier_appel and COI_PAGE_DELAY:
                time.sleep(COI_PAGE_DELAY)
            premier_appel = False

            try:
                bruts = fetch_page(categorie, page)
            except Exception as exc:
                # L'API renvoie 400 au-dela de la derniere page : fin normale.
                if "400" not in str(exc):
                    print(f"COI : categorie {categorie} page {page} en echec "
                          f"({str(exc)[:60]}).")
                break

            if not bruts:
                break

            neufs_page = 0
            for brut in bruts:
                item = normalize(brut)
                # Le dedoublonnage compte double ici : les categories annuelles
                # se recouvrent largement.
                if item["id"] in seen_ids or item["id"] in vus_ce_run:
                    continue
                if not complet and not est_recent(date_publication(brut)):
                    ignores_anciens += 1
                    continue

                vus_ce_run.add(item["id"])
                nouveaux.append(item)
                neufs_page += 1
                if limite is not None and len(nouveaux) >= limite:
                    print(f"COI : plafond premier lancement atteint ({limite} avis).")
                    return nouveaux

            if not complet and neufs_page == 0:
                break

    if ignores_anciens:
        print(f"  COI : {ignores_anciens} avis trop ancien(s) ecarte(s).")
    return nouveaux


class CoiScraper(BaseScraper):
    source_key = "coi"
    nom = "Commission ocean Indien"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
