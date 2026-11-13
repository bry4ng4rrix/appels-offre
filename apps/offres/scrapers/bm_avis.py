"""Avis de passation de marches de la Banque mondiale.

Source : la page /fr/projects-operations/opportunities du site s'appuie sur
l'API publique https://search.worldbank.org/api/v2/procnotices (sans cle).

Contrairement aux projets (scraper_banquemondiale.py), ces avis ont une vraie
date limite de depot : ce sont des opportunites auxquelles on candidate.

Trois particularites de l'API, toutes verifiees :
  - le filtre pays est "project_ctry_name_exact" et attend un NOM de pays.
    countryname_exact et countrycode sont acceptes mais ignores : ils
    renvoient les 415 000 avis du monde entier.
  - "notice_type_exact" n'accepte qu'une valeur a la fois, d'ou une requete
    par type. Cela evite surtout de rapatrier les "Contract Award", qui sont
    des marches deja attribues et representent 72 % du volume.
  - "noticedate" est au format "16-Aug-2026", alors que les dates de depot
    sont en ISO.
"""

import re
from datetime import date
from html import unescape

from .base import BaseScraper
from .http import get_json
from Offre.sources import (
    BM_AVIS_URL,
    BM_AVIS_DETAIL_URL,
    BM_AVIS_PAYS,
    BM_AVIS_TYPES,
    BM_AVIS_OUVERTS_SEULEMENT,
    BM_AVIS_SANS_DATE_MAX_JOURS,
    BM_AVIS_PAGE_SIZE,
    BM_AVIS_MAX_PAGES,
    FIRST_RUN_MAX_ITEMS,
)

HEADERS = {"User-Agent": "veille-appels/1.0"}


def fetch_page(pays: str, type_avis: str, offset: int) -> list:
    """Une page d'avis, du plus recemment publie au plus ancien."""
    params = {
        "format": "json",
        "rows": BM_AVIS_PAGE_SIZE,
        "os": offset,
        "srt": "noticedate",
        "order": "desc",
    }
    if pays:
        params["project_ctry_name_exact"] = pays
    if type_avis:
        params["notice_type_exact"] = type_avis

    avis = get_json(BM_AVIS_URL, HEADERS, params).get("procnotices", [])
    # L'API alterne entre liste et dict selon les endpoints : on normalise.
    return avis if isinstance(avis, list) else list(avis.values())


MOIS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def echeance_iso(avis: dict) -> str:
    return str(avis.get("submission_deadline_date") or "")[:10]


def date_publication(avis: dict):
    """noticedate est au format '16-Aug-2026'. Renvoie une date ou None.

    Table de mois explicite plutot que strptime("%d-%b-%Y") : %b depend de la
    locale du systeme et casserait sur une machine configuree en francais.
    """
    morceaux = str(avis.get("noticedate") or "").split("-")
    if len(morceaux) != 3:
        return None
    jour, mois, annee = morceaux
    numero = MOIS.get(mois[:3].lower())
    if not numero:
        return None
    try:
        return date(int(annee), numero, int(jour))
    except ValueError:
        return None


def est_ouvert(avis: dict) -> bool:
    """Vrai si l'avis est encore susceptible d'accepter une candidature."""
    iso = echeance_iso(avis)
    if iso:
        try:
            return date.fromisoformat(iso) >= date.today()
        except ValueError:
            pass

    # Sans date limite exploitable, on se rabat sur la date de publication :
    # tous les avis non dates observes pour Madagascar ont plus de 90 jours,
    # le plus ancien remontant a 2011.
    publie = date_publication(avis)
    if publie is None:
        return True  # ni echeance ni date de publication : a verifier a la main
    return (date.today() - publie).days <= BM_AVIS_SANS_DATE_MAX_JOURS


def texte_brut(html: str) -> str:
    """Convertit le notice_text (HTML) en texte lisible.

    BeautifulSoup serait plus robuste mais couterait un parse complet par avis
    pour un contenu simple : quelques balises de mise en forme et des entites.
    """
    if not html:
        return ""
    coupures = r"<br\s*/?>|</p>|</div>|</li>|</tr>"
    texte = re.sub(coupures, "\n", html, flags=re.I)
    texte = re.sub(r"<[^>]+>", "", texte)
    texte = unescape(texte)
    texte = re.sub(r"[ \t]+", " ", texte)
    texte = re.sub(r"\n\s*\n+", "\n\n", texte)
    return texte.strip()


def normalize(avis: dict) -> dict:
    """Ramene un avis au format commun aux autres sources."""
    titre = avis.get("bid_description") or avis.get("project_name") or ""
    type_avis = avis.get("notice_type") or ""
    # Le type est porte dans le titre : sans lui, un intitule comme "Fourniture
    # de materiels" ne dit pas s'il s'agit d'un appel d'offres ou d'une simple
    # manifestation d'interet.
    if type_avis and type_avis.lower() not in titre.lower():
        titre = f"[{type_avis}] {titre}"

    return {
        "id": avis.get("id", ""),
        "source": "banquemondiale-avis",
        "titre": titre,
        "organisation": (avis.get("contact_organization")
                         or avis.get("project_name") or ""),
        "pays": avis.get("project_ctry_name", ""),
        "date_limite": echeance_iso(avis),
        # notice_text vient dans la meme requete : aucun cout supplementaire.
        "description": texte_brut(avis.get("notice_text")),
        "lien": BM_AVIS_DETAIL_URL.format(id=avis.get("id", "")),
    }


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Parcourt les avis, meme logique incrementale que les autres sources."""
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    for pays in (BM_AVIS_PAYS or [""]):
        for type_avis in (BM_AVIS_TYPES or [""]):
            for page in range(BM_AVIS_MAX_PAGES):
                bruts = fetch_page(pays, type_avis, page * BM_AVIS_PAGE_SIZE)
                if not bruts:
                    break

                arret = False
                for brut in bruts:
                    item = normalize(brut)
                    if not item["id"]:
                        continue
                    if item["id"] in seen_ids:
                        if complet:
                            continue
                        # Tries par date de publication : tout ce qui suit est
                        # plus ancien, donc deja traite.
                        arret = True
                        break
                    if item["id"] in vus_ce_run:
                        continue
                    if BM_AVIS_OUVERTS_SEULEMENT and not est_ouvert(brut):
                        continue

                    vus_ce_run.add(item["id"])
                    nouveaux.append(item)
                    if limite is not None and len(nouveaux) >= limite:
                        print(f"Avis Banque mondiale : plafond premier lancement "
                              f"atteint ({limite} avis).")
                        return nouveaux

                if arret:
                    break

    return nouveaux


class BanqueMondialeAvisScraper(BaseScraper):
    source_key = "banquemondiale-avis"
    nom = "Banque mondiale (avis)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
