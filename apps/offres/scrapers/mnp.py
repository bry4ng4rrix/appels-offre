"""Appels d'offres de Madagascar National Parks.

Source : https://parcs-madagascar.com/appel-doffre/

Gestionnaire du reseau d'aires protegees malgaches, finance par des bailleurs
internationaux (Banque mondiale, KfW). WordPress avec un type de contenu
dedie `appel_offre`.

Constate le 21/08/2026 :
  - robots.txt n'interdit rien et impose "Crawl-delay: 10", respecte ici.
  - L'API REST WordPress N'EXPOSE PAS ce type de contenu (elle ne compte que
    3 articles, le plugin Advanced Access Manager restreignant l'acces). On
    passe donc par le HTML, contrairement au FID.
  - Chaque avis porte une VRAIE date limite en toutes lettres
    ("Date limite 14 Septembre 2026"), ce qui evite tout repli sur une date
    de publication.

Les titres contiennent des emoji decoratifs (megaphone) que le site place
aussi dans les URL sous forme percent-encodee : ils sont retires du titre et
neutralises dans l'identifiant.
"""

import re
import time
from datetime import date
from urllib.parse import unquote

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import (
    MNP_BASE_URL,
    MNP_PAGE_DELAY,
    MNP_MAX_PAGES,
    MNP_OUVERTS_SEULEMENT,
    FIRST_RUN_MAX_ITEMS,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr,en;q=0.8",
}

# Mois en toutes lettres : aucune ambiguite, contrairement aux abreviations
# a trois lettres de la BAD ou juin et juillet se confondent.
MOIS_FR = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10,
    "novembre": 11, "decembre": 12,
}

ACCENTS = str.maketrans("àâäéèêëîïôöûüùç", "aaaeeeeiioouuuc")


def sans_accents(texte: str) -> str:
    return (texte or "").lower().translate(ACCENTS)


def nettoyer(texte: str) -> str:
    """Retire emoji decoratifs, ponctuation parasite et espaces multiples."""
    # Emoji et symboles hors du plan multilingue de base.
    texte = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️]", " ", texte or "")
    return re.sub(r"\s+", " ", texte).strip(" -–—:")


def date_limite(texte: str) -> str:
    """Extrait "Date limite 14 Septembre 2026" -> "2026-09-14"."""
    m = re.search(r"Date\s+limite\s*:?\s*(\d{1,2})\s+(\w+)\s+(\d{4})",
                  texte or "", re.I | re.UNICODE)
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


def identifiant(lien: str) -> str:
    """Identifiant stable derive du slug, emoji percent-encodes neutralises."""
    slug = unquote((lien or "").rstrip("/").split("/")[-1])
    slug = nettoyer(slug)
    slug = re.sub(r"[^a-z0-9]+", "-", sans_accents(slug)).strip("-")
    return f"mnp-{slug[:90]}" if slug else ""


def est_ouvert(echeance: str) -> bool:
    """Un avis sans date limite lisible est conserve : on ne peut pas le
    declarer clos."""
    if not echeance:
        return True
    try:
        return date.fromisoformat(echeance) >= date.today()
    except ValueError:
        return True


def fetch_page(page: int) -> list:
    """Une page d'avis. page 1 = la plus recente."""
    url = MNP_BASE_URL if page <= 1 else f"{MNP_BASE_URL.rstrip('/')}/page/{page}/"
    soup = BeautifulSoup(get_html(url, HEADERS, timeout=60), "html.parser")

    avis = []
    for bloc in soup.select("div.descwrap"):
        titre_el = bloc.find(["h2", "h3"])
        lien_el = bloc.find("a", href=True)
        if titre_el is None or lien_el is None:
            continue
        avis.append({
            "titre": titre_el.get_text(" ", strip=True),
            "lien": lien_el.get("href", ""),
            # Le bloc porte la date limite ET l'extrait descriptif.
            "texte": bloc.get_text(" ", strip=True),
        })
    return avis


def normalize(brut: dict) -> dict:
    """Ramene un avis au format commun aux autres sources."""
    titre = nettoyer(brut["titre"])
    echeance = date_limite(brut["texte"])

    # L'extrait est le bloc prive de la mention de date et du titre repete.
    extrait = re.sub(r"Date\s+limite\s*:?\s*\d{1,2}\s+\w+\s+\d{4}", "",
                     brut["texte"], flags=re.I)
    extrait = nettoyer(extrait).replace(titre, "").strip(" .")

    return {
        "id": identifiant(brut["lien"]),
        "source": "mnp",
        "titre": titre,
        "organisation": "Madagascar National Parks",
        "pays": "Madagascar",
        "date_limite": echeance,
        "description": (f"Clôture le {echeance}. " if echeance else "") + extrait[:1200],
        "lien": brut["lien"],
    }


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Parcourt les pages, meme logique incrementale que les autres sources."""
    nouveaux = []
    vus_ce_run = set()
    ignores_clos = 0
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    for page in range(1, MNP_MAX_PAGES + 1):
        if page > 1 and MNP_PAGE_DELAY:
            # Consigne du robots.txt du site, pas un reglage de confort.
            time.sleep(MNP_PAGE_DELAY)

        try:
            bruts = fetch_page(page)
        except Exception as exc:
            # Au-dela de la derniere page le site renvoie 404 : fin normale.
            if "404" not in str(exc):
                print(f"MNP : page {page} inaccessible ({str(exc)[:60]}).")
            break

        if not bruts:
            break

        neufs_page = 0
        for brut in bruts:
            item = normalize(brut)
            if not item["id"] or item["id"] in seen_ids or item["id"] in vus_ce_run:
                continue
            if MNP_OUVERTS_SEULEMENT and not est_ouvert(item["date_limite"]):
                ignores_clos += 1
                continue

            vus_ce_run.add(item["id"])
            nouveaux.append(item)
            neufs_page += 1
            if limite is not None and len(nouveaux) >= limite:
                print(f"MNP : plafond premier lancement atteint ({limite} avis).")
                return nouveaux

        if not complet and neufs_page == 0:
            break

    if ignores_clos:
        print(f"  MNP : {ignores_clos} avis deja clos ecarte(s).")
    return nouveaux


class MnpScraper(BaseScraper):
    source_key = "mnp"
    nom = "Madagascar National Parks"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
