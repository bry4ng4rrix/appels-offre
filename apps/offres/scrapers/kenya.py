"""Marches publics du Kenya (PPIP, via l'API du portail).

Source : GET https://tenders.go.ke/api/active-tenders?page=<n>

Constate le 14/09/2026 :

  - La reponse est une page Laravel : `data`, `current_page`, `last_page`,
    `total`. Dix avis par page, 289 actifs au sondage. Trie par date de
    cloture croissante : chaque passage lit toutes les pages.

  - Chaque avis porte title, tender_ref, published_at, close_at, l'entite
    (pe.name), la methode (procurement_method.title), la categorie
    (procurement_category.title), le drapeau is_reservation (AGPO) et les
    documents joints. L'identifiant technique est `id` ; la fiche du portail
    est /tenders/<id>.

  - Les dates sont "2026-09-15 00:00:00".

  - 60 requetes par minute au plus : KE_PAGE_DELAY tient le parcours sous
    ce seuil ; un 429 fait attendre la minute puis reessayer une fois, et un
    second 429 arrete la collecte en conservant l'acquis.
"""

import re
import time
from datetime import date

from .base import BaseScraper
from .http import get_json
from Offre.sources import (KE_API, KE_FICHE, KE_PAGE_DELAY, KE_MAX_PAGES,
                    KE_METHODES_EXCLUES, KE_ATTENTE_429, FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "application/json",
           "X-Requested-With": "XMLHttpRequest",
           "Referer": "https://tenders.go.ke/tenders"}


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


def est_exclu(avis: dict) -> bool:
    """Reserve AGPO, ou procedure fermee (restreinte, directe)."""
    if avis.get("is_reservation"):
        return True
    methode = texte_brut((avis.get("procurement_method") or {}).get("title")).lower()
    return any(mot in methode for mot in KE_METHODES_EXCLUES)


def normalize(avis: dict) -> dict:
    titre = texte_brut(avis.get("title"))
    methode = texte_brut((avis.get("procurement_method") or {}).get("title"))
    categorie = texte_brut((avis.get("procurement_category") or {}).get("title"))
    entite = texte_brut((avis.get("pe") or {}).get("name"))
    description = texte_brut(avis.get("description"))

    details = [x for x in (methode, categorie) if x]
    if texte_brut(avis.get("tender_ref")):
        details.append(f"Ref {texte_brut(avis['tender_ref'])}")
    if avis.get("tender_fee"):
        details.append(f"Tender fee {avis['tender_fee']} KES")
    corps = description if description and description.upper() != titre.upper() else titre

    return {
        "id": f"ke-{avis['id']}",
        "source": "kenya",
        "titre": titre or texte_brut(avis.get("tender_ref")) or "Tender",
        "organisation": entite,
        "pays": "Kenya",
        "date_limite": date_iso(avis.get("close_at")),
        "date_publication": date_iso(avis.get("published_at")),
        "description": ". ".join(details + [corps]) if details else corps,
        "lien": f"{KE_FICHE}{avis['id']}",
    }


def page_json(page: int) -> dict:
    """Une page de l'API. Sur 429, attend la fin de la minute et reessaie.

    La reprise generique de web.py attend 1 s puis 2 s : trop court pour une
    limite exprimee par minute, et le 16/09/2026 la premiere page repondait
    deja 429 -- le compteur n'est manifestement pas remis a zero entre nos
    passages, ou il est partage avec d'autres clients.
    """
    try:
        return get_json(KE_API, HEADERS, params={"page": page}, timeout=90)
    except Exception as exc:
        if getattr(getattr(exc, "response", None), "status_code", None) != 429:
            raise
        print(f"  Kenya : limite de debit atteinte, attente de {KE_ATTENTE_429} s.")
        time.sleep(KE_ATTENTE_429)
        return get_json(KE_API, HEADERS, params={"page": page}, timeout=90)


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Lit toutes les pages des avis actifs. Le tri par echeance interdit
    l'arret sur page connue ; `complet` ne change que le plafond."""
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)
    aujourd_hui = date.today().isoformat()
    derniere = KE_MAX_PAGES

    page = 1
    while page <= min(derniere, KE_MAX_PAGES):
        if page > 1 and KE_PAGE_DELAY:
            time.sleep(KE_PAGE_DELAY)
        try:
            reponse = page_json(page)
        except Exception as exc:
            print(f"Kenya : page {page} inaccessible ({str(exc)[:70]}).")
            print(f"  {len(nouveaux)} avis deja collecte(s) sont conserves.")
            return nouveaux

        avis_page = reponse.get("data") or []
        derniere = int(reponse.get("last_page") or page)
        if not avis_page:
            if page == 1:
                print("Kenya : reponse vide, l'API a peut-etre change.")
            break

        for avis in avis_page:
            if not avis.get("id"):
                continue
            ident = f"ke-{avis['id']}"
            if ident in seen_ids or ident in vus_ce_run:
                continue
            vus_ce_run.add(ident)
            if est_exclu(avis):
                continue
            item = normalize(avis)
            if item["date_limite"] and item["date_limite"] < aujourd_hui:
                continue
            nouveaux.append(item)
            if limite is not None and len(nouveaux) >= limite:
                print(f"Kenya : plafond premier lancement atteint ({limite} avis).")
                return nouveaux
        page += 1

    return nouveaux


class KenyaScraper(BaseScraper):
    source_key = "kenya"
    nom = "Kenya (PPIP)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
