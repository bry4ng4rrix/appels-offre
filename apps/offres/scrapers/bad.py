"""Avis de passation de marches de la Banque africaine de developpement.

Source : https://www.afdb.org/fr/documents/project-related-procurement

La page est rendue cote serveur (Drupal, vue "documents"), sans chargement
AJAX : un GET suffit, pas besoin de navigateur.

Cadre verifie le 20/08/2026 :
  - robots.txt autorise ce chemin, mais impose "Crawl-delay: 10". Ce delai est
    respecte entre chaque page (BAD_PAGE_DELAY) : c'est une consigne du site.
  - Les conditions d'utilisation n'interdisent PAS la collecte. Elles
    interdisent de "resell, redistribute or create derivative works for
    commercial purposes" sans accord ecrit. Usage interne uniquement, donc.

Limite connue : la liste ne porte pas de date limite de depot, seulement une
date de publication. L'echeance figure dans le PDF du dossier, non telecharge.
Le champ date_limite reste donc vide pour cette source.
"""

import re
import time

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import (
    BAD_BASE_URL,
    BAD_DETAIL_BASE,
    BAD_PAGE_DELAY,
    BAD_MAX_PAGES,
    BAD_TYPES_EXCLUS,
    FIRST_RUN_MAX_ITEMS,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr,en;q=0.8",
}

# Mois francais tels que rendus par le site ("20-aou-2026").
# juin et juillet sont volontairement en 4 lettres : tronques a 3, ils
# donneraient tous deux "jui" et un avis de juillet serait date de juin.
# Un jeton ambigu renvoie None plutot qu'une date fausse.
MOIS_FR = {
    "jan": 1, "fev": 2, "mar": 3, "avr": 4, "mai": 5,
    "juin": 6, "juil": 7, "aou": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

ACCENTS = str.maketrans("àâäéèêëîïôöûüùç", "aaaeeeeiioouuuc")


def sans_accents(texte: str) -> str:
    return (texte or "").lower().translate(ACCENTS)


def date_publication_iso(brut: str) -> str:
    """Convertit "20-aou-2026" en "2026-08-20". Chaine vide si illisible."""
    m = re.match(r"\s*(\d{1,2})\s*-\s*(.+?)\s*-\s*(\d{4})", brut or "")
    if not m:
        return ""
    jour, mois_txt, annee = m.groups()
    mois_txt = sans_accents(mois_txt).rstrip(".")

    # Correspondance la plus longue d'abord : "juil" avant "jui".
    mois = None
    for cle in sorted(MOIS_FR, key=len, reverse=True):
        if mois_txt.startswith(cle):
            mois = MOIS_FR[cle]
            break
    if mois is None:
        return ""
    try:
        from datetime import date
        return date(int(annee), mois, int(jour)).isoformat()
    except ValueError:
        return ""


def type_et_pays(titre: str) -> tuple:
    """Extrait le type d'avis et le pays du titre.

    Les titres suivent "TYPE - Pays - Intitule" ("EOI - Liberia - Provision
    of..."). Verifie sur 40 titres : le pays est en 2e position dans tous.
    """
    morceaux = [p.strip() for p in titre.split(" - ")]
    type_avis = morceaux[0] if len(morceaux) >= 2 else ""
    pays = morceaux[1] if len(morceaux) >= 3 else ""
    # Un "pays" trop long est en fait un bout d'intitule : le titre ne suivait
    # pas le format attendu.
    if len(pays) > 40:
        pays = ""
    return type_avis, pays


def est_exclu(titre: str) -> bool:
    """Vrai pour les marches deja attribues, sans interet pour une veille."""
    bas = sans_accents(titre)
    return any(sans_accents(t) in bas for t in BAD_TYPES_EXCLUS)


def identifiant(lien: str) -> str:
    """Le slug de la fiche sert d'identifiant stable."""
    slug = (lien or "").rstrip("/").split("/")[-1]
    return f"bad-{slug}" if slug else ""


def fetch_page(page: int) -> list:
    """Une page de 20 avis, du plus recemment publie au plus ancien."""
    url = BAD_BASE_URL if page == 0 else f"{BAD_BASE_URL}?page={page}"
    soup = BeautifulSoup(get_html(url, HEADERS), "html.parser")

    avis = []
    for bloc in soup.select("div.views-field-title"):
        lien_el = bloc.find("a")
        if lien_el is None:
            continue

        # Remonter a la carte pour recuperer la date, qui vit dans un frere.
        carte = bloc.find_parent("div", class_=re.compile(r"col-"))
        date_el = (carte.select_one(".views-field-field-publication-date")
                   if carte else None)

        href = lien_el.get("href", "")
        avis.append({
            "titre": lien_el.get_text(" ", strip=True),
            "href": href if href.startswith("http") else BAD_DETAIL_BASE + href,
            "date_publication": date_el.get_text(" ", strip=True) if date_el else "",
        })
    return avis


def normalize(avis: dict) -> dict:
    """Ramene un avis au format commun aux autres sources."""
    titre = avis["titre"]
    type_avis, pays = type_et_pays(titre)
    publie = date_publication_iso(avis.get("date_publication", ""))

    # La date de publication n'a pas de colonne dediee : la porter dans la
    # description evite de la perdre, et renseigne sur la fraicheur de l'avis.
    description = f"Type : {type_avis}. Publié le {publie or '?'}."

    return {
        "id": identifiant(avis["href"]),
        "source": "bad",
        "titre": titre,
        "organisation": "Banque africaine de developpement",
        "pays": pays,
        # La liste ne porte pas d'echeance de depot : elle est dans le PDF.
        "date_limite": "",
        # Elle porte en revanche la date de PUBLICATION, seul repere d'age
        # dont on dispose pour cette source. Sans elle, une offre publiee il y
        # a six mois passerait pour aussi fraiche qu'une d'hier.
        "date_publication": publie or "",
        "description": description,
        "lien": avis["href"],
    }


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Parcourt les pages, meme logique incrementale que les autres sources.

    L'arret porte sur une page entierement connue et non sur le premier ID
    connu : c'est la lecon du bug UNjobnet, ou une annonce epinglee en tete
    stoppait la collecte a chaque run.
    """
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    for page in range(BAD_MAX_PAGES):
        if page > 0 and BAD_PAGE_DELAY:
            # Consigne du robots.txt du site, pas un reglage de confort.
            time.sleep(BAD_PAGE_DELAY)

        try:
            bruts = fetch_page(page)
        except Exception as exc:
            print(f"BAD : page {page} inaccessible ({str(exc)[:70]}).")
            print(f"  {len(nouveaux)} avis deja collecte(s) sont conserves.")
            return nouveaux

        if not bruts:
            break

        neufs_page = 0
        for brut in bruts:
            if est_exclu(brut["titre"]):
                continue
            item = normalize(brut)
            if not item["id"]:
                continue
            if item["id"] in seen_ids or item["id"] in vus_ce_run:
                continue

            vus_ce_run.add(item["id"])
            nouveaux.append(item)
            neufs_page += 1
            if limite is not None and len(nouveaux) >= limite:
                print(f"BAD : plafond premier lancement atteint ({limite} avis).")
                return nouveaux

        if not complet and neufs_page == 0:
            return nouveaux

    return nouveaux


class BadScraper(BaseScraper):
    source_key = "bad"
    nom = "Banque africaine de dev."

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
