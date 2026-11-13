"""Appels d'offres du FID Madagascar, via l'API REST WordPress.

Source : https://www.fid.mg/wp-json/wp/v2/posts

Fonds d'Intervention pour le Developpement, bailleur malgache. Le site est
sous WordPress et expose son API REST publiquement : on l'interroge plutot que
de scraper la page /appels-doffres/.

Pourquoi l'API et non le HTML -- le scraping de la liste posait trois
problemes que l'API supprime :
  - la page n'affiche une date de cloture que pour 8 avis sur 100, le reste
    etant des archives indiscernables des avis en cours ;
  - il fallait deviner la fraicheur depuis la date terminant le slug, absente
    d'un tiers des URL ;
  - la liste melangeait appels d'offres, resultats et attributions.

L'API donne une date de publication fiable pour chaque avis et permet de
filtrer par categorie, ce qui ecarte d'emblee resultats et attributions.

Constate le 21/08/2026 : robots.txt autorise tout ("Disallow:" vide) et
l'API repond sans authentification.
"""

import re
import time
from datetime import date
from html import unescape

from .base import BaseScraper
from .http import get_json
from Offre.sources import (
    FID_API_URL,
    FID_CATEGORIES,
    FID_PAGE_SIZE,
    FID_PAGE_DELAY,
    FID_MAX_PAGES,
    FID_MAX_JOURS,
    FIRST_RUN_MAX_ITEMS,
)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "application/json"}

# Les mois sont ecrits en toutes lettres ("07 Septembre 2026") : aucune
# ambiguite, contrairement aux abreviations a trois lettres de la BAD ou
# juin et juillet se confondent.
MOIS_FR = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10,
    "novembre": 11, "decembre": 12,
}

ACCENTS = str.maketrans("àâäéèêëîïôöûüùç", "aaaeeeeiioouuuc")


def sans_accents(texte: str) -> str:
    return (texte or "").lower().translate(ACCENTS)


def texte_brut(html: str) -> str:
    """Retire balises et entites d'un champ rendu par WordPress."""
    texte = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", unescape(texte)).strip()


def date_cloture(contenu: str) -> str:
    """Extrait "Date de cloture : 07 Septembre 2026" -> "2026-09-07".

    Chaine vide si absent ou illisible. On ne devine jamais depuis le titre :
    la date qui y figure est tantot la cloture, tantot la publication.
    """
    m = re.search(
        r"Date\s+de\s+cl\w*ture\s*:?\s*(\d{1,2})\s+(\w+)\s+(\d{4})",
        contenu or "", re.I | re.UNICODE)
    if not m:
        return ""
    jour, mois_txt, annee = m.groups()
    mois = MOIS_FR.get(sans_accents(mois_txt))
    if not mois:
        return ""
    try:
        return date(int(annee), mois, int(jour)).isoformat()
    except ValueError:
        return ""


def date_publication(brut: dict):
    """Date de publication WordPress ("2026-08-19T10:22:00"), ou None."""
    valeur = (brut.get("date") or "")[:10]
    try:
        return date.fromisoformat(valeur)
    except ValueError:
        return None


def est_ouvert(echeance: str, publie) -> bool:
    """Vrai si l'avis peut encore accepter une candidature.

    La date de cloture prime. A defaut, on se fie a la fraicheur : le FID
    publie 740 appels d'offres dont l'immense majorite est archivee, et un
    avis publie il y a plus de FID_MAX_JOURS est clos en pratique.
    """
    if echeance:
        try:
            return date.fromisoformat(echeance) >= date.today()
        except ValueError:
            pass
    if publie is None:
        return True          # aucun indice : on ne peut pas le declarer clos
    return (date.today() - publie).days <= FID_MAX_JOURS


def fetch_page(categorie: int, page: int) -> list:
    """Une page d'avis d'une categorie, du plus recent au plus ancien."""
    return get_json(FID_API_URL, HEADERS, {
        "categories": categorie,
        "per_page": FID_PAGE_SIZE,
        "page": page,
        "orderby": "date",
        "order": "desc",
        # Limiter les champs : le contenu complet de 100 articles pese lourd.
        "_fields": "id,date,link,title,content",
    })


def normalize(brut: dict) -> dict:
    """Ramene un avis au format commun aux autres sources."""
    titre = texte_brut((brut.get("title") or {}).get("rendered", ""))
    contenu = texte_brut((brut.get("content") or {}).get("rendered", ""))
    echeance = date_cloture(contenu)
    publie = date_publication(brut)

    details = [f"Publie le {publie}" if publie else "",
               f"Cloture le {echeance}" if echeance
               else "Date de cloture non precisee"]

    return {
        "id": f"fid-{brut.get('id')}",
        "source": "fid",
        "titre": titre,
        "organisation": "Fonds d'Intervention pour le Developpement (FID)",
        "pays": "Madagascar",
        "date_limite": echeance,
        # Publiee par l'API WordPress ; utile quand la cloture manque.
        "date_publication": publie or "",
        "description": ". ".join(d for d in details if d) + ". " + contenu[:1500],
        "lien": brut.get("link", ""),
    }


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Parcourt les categories d'appels d'offres, du plus recent au plus ancien."""
    nouveaux = []
    vus_ce_run = set()
    ignores_clos = 0
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)
    premier_appel = True

    for categorie in FID_CATEGORIES:
        for page in range(1, FID_MAX_PAGES + 1):
            if not premier_appel and FID_PAGE_DELAY:
                time.sleep(FID_PAGE_DELAY)
            premier_appel = False

            try:
                bruts = fetch_page(categorie, page)
            except Exception as exc:
                # L'API renvoie 400 au-dela de la derniere page : c'est une fin
                # de pagination normale, pas une panne.
                if "400" not in str(exc):
                    print(f"FID : categorie {categorie} page {page} en echec "
                          f"({str(exc)[:60]}).")
                break

            if not bruts:
                break

            neufs_page = 0
            for brut in bruts:
                item = normalize(brut)
                if item["id"] in seen_ids or item["id"] in vus_ce_run:
                    continue
                if not est_ouvert(item["date_limite"], date_publication(brut)):
                    ignores_clos += 1
                    continue

                vus_ce_run.add(item["id"])
                nouveaux.append(item)
                neufs_page += 1
                if limite is not None and len(nouveaux) >= limite:
                    print(f"FID : plafond premier lancement atteint ({limite} avis).")
                    return nouveaux

            # Les avis etant tries par date decroissante, une page sans aucun
            # avis retenu signifie qu'on est sorti de la fenetre utile.
            if not complet and neufs_page == 0:
                break

    if ignores_clos:
        print(f"  FID : {ignores_clos} avis clos ou trop anciens ecarte(s).")
    return nouveaux


class FidScraper(BaseScraper):
    source_key = "fid"
    nom = "FID Madagascar"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
