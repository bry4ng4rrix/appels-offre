"""Portails publics a API JSON propre, sans format commun (ni OCDS ni RSS).

- Suisse, simap.ch : appels de la Confederation, des cantons et des communes.
- New York, City Record : appels de la ville (jeu de donnees Socrata).
"""

import time
from datetime import date, timedelta

from .base import BaseScraper
from .fid import texte_brut
from .http import get_json
from Offre.sources import (SIMAP_URL, SIMAP_FICHE, SIMAP_FENETRE_JOURS, SIMAP_MAX_PAGES,
                           NYC_URL, NYC_FICHE, FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "application/json"}


def langue(champ: dict | None) -> str:
    """Libelle multilingue de simap : le francais d'abord."""
    champ = champ or {}
    return next((champ[l].strip() for l in ("fr", "en", "de", "it") if champ.get(l)), "")


def normalize_simap(projet: dict) -> dict | None:
    titre = langue(projet.get("title"))
    if not projet.get("id") or not titre:
        return None
    lieu = projet.get("orderAddress") or {}
    ville = langue(lieu.get("city"))
    return {
        "id": f"ch-{projet['id']}",
        "source": "suisse",
        "titre": titre,
        "organisation": langue(projet.get("procOfficeName")),
        "pays": "Suisse",
        # La liste ne donne pas l'echeance : elle est dans la fiche.
        "date_limite": "",
        "date_publication": projet.get("publicationDate") or "",
        "description": ". ".join(x for x in (
            f"Projet {projet.get('projectNumber')}", projet.get("projectSubType"),
            projet.get("processType"), f"{ville} ({lieu.get('cantonId')})" if ville else "", titre) if x),
        "lien": SIMAP_FICHE.format(projet["id"]),
    }


class SuisseScraper(BaseScraper):
    source_key = "suisse"
    nom = "Suisse (simap.ch)"
    site = "https://www.simap.ch/"

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        depuis = (date.today() - timedelta(days=SIMAP_FENETRE_JOURS)).isoformat()
        nouveaux, vus, curseur = [], set(seen_ids), ""
        for page in range(SIMAP_MAX_PAGES):
            if page:
                time.sleep(1)
            params = {"newestPublicationFrom": depuis, "newestPubTypes": "tender"}
            if curseur:
                params["lastItem"] = curseur
            try:
                reponse = get_json(SIMAP_URL, HEADERS, params)
            except Exception as exc:
                print(f"{self.nom} : page {page + 1} en echec ({str(exc)[:60]}).")
                break
            for item in filter(None, map(normalize_simap, reponse.get("projects") or [])):
                if item["id"] not in vus:
                    vus.add(item["id"])
                    nouveaux.append(item)
            suivant = (reponse.get("pagination") or {}).get("lastItem")
            if not reponse.get("projects") or not suivant or suivant == curseur:
                break
            curseur = suivant
        return nouveaux[:limite] if limite else nouveaux


def normalize_nyc(avis: dict) -> dict | None:
    ident, titre = avis.get("request_id"), (avis.get("short_title") or "").strip()
    if not ident or not titre:
        return None
    return {
        "id": f"nyc-{ident}",
        "source": "new_york",
        "titre": titre,
        "organisation": f"Ville de New York, {avis.get('agency_name', '')}".rstrip(", "),
        "pays": "États-Unis",
        "date_limite": (avis.get("due_date") or "")[:10],
        "date_publication": (avis.get("start_date") or "")[:10],
        "description": ". ".join(x for x in (
            avis.get("selection_method_description"), avis.get("category_description"),
            texte_brut(avis.get("additional_description_1") or "")[:1200]) if x),
        "lien": NYC_FICHE.format(ident),
    }


class NewYorkScraper(BaseScraper):
    source_key = "new_york"
    nom = "New York (City Record)"
    site = "https://a856-cityrecord.nyc.gov/"

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        lignes = get_json(NYC_URL, HEADERS, {
            "$limit": 1000, "$order": "start_date DESC",
            "$where": (f"type_of_notice_description='Solicitation' "
                       f"AND due_date >= '{date.today().isoformat()}'")}, timeout=90)
        vus, nouveaux = set(seen_ids), []
        for item in filter(None, map(normalize_nyc, lignes)):
            if item["id"] not in vus:
                vus.add(item["id"])
                nouveaux.append(item)
        return nouveaux[:limite] if limite else nouveaux
