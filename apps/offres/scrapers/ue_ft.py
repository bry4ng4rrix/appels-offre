"""Portail Funding & Tenders de l'Union europeenne.

Source : API de recherche du portail (POST multipart, cle publique SEDIA).
Couvre trois familles : marches des institutions et delegations de l'UE
(type 0), subventions des programmes (type 1) et appels EuropeAid de l'aide
exterieure (type 2). Chaque champ de metadata est une liste de chaines.
"""

import json
import time
from datetime import date, timedelta

from .base import BaseScraper
from .fid import texte_brut
from .http import post_multipart_json
from Offre.sources import (EU_FT_URL, EU_FT_SITE, EU_FT_TYPES, EU_FT_PAGE_SIZE,
                           EU_FT_MAX_PAGES, EU_FT_PAGE_DELAY, EU_FT_SANS_DATE_MAX_JOURS,
                           FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "application/json"}
FAMILLES = {"0": "Marche de l'UE", "1": "Subvention UE", "2": "Appel EuropeAid"}
REQUETE = {"bool": {"must": [{"terms": {"type": EU_FT_TYPES}},
                             {"terms": {"status": ["31094502"]}}]}}


def champ(meta: dict, cle: str) -> str:
    valeurs = meta.get(cle) or []
    return str(valeurs[0]).strip() if valeurs else ""


def echeance(meta: dict, aujourdhui: str) -> str:
    """Prochaine echeance : les appels en plusieurs vagues en listent plusieurs."""
    dates = sorted(d[:10] for d in meta.get("deadlineDate") or meta.get("closingDate") or [] if d)
    return next((d for d in dates if d >= aujourdhui), dates[-1] if dates else "")


def acheteur(meta: dict, famille: str) -> str:
    try:
        autorites = json.loads(champ(meta, "cftLeadContractingAuthorityCode") or "[]")
        return autorites[0]["name"]
    except (ValueError, LookupError, TypeError):
        return "Commission europeenne (EuropeAid)" if famille == "2" else "Commission europeenne"


def normalize(resultat: dict, aujourdhui: str) -> dict | None:
    meta = resultat.get("metadata") or {}
    ident, famille = champ(meta, "identifier"), champ(meta, "type")
    titre = champ(meta, "title") or resultat.get("summary", "")
    if not ident or not titre:
        return None
    appel = champ(meta, "callTitle")
    if famille == "1" and appel and appel != titre:
        titre = f"{appel} - {titre}"
    # EuropeAid/188041/DD/ACT/JO : le dernier segment est le pays beneficiaire.
    pays = "Madagascar" if famille == "2" and ident.endswith("/MG") else ""
    reference = champ(meta, "callIdentifier") or ident
    return {
        "id": f"euft-{ident}",
        "source": "ue_ft",
        "titre": titre,
        "organisation": acheteur(meta, famille),
        "pays": pays,
        "date_limite": echeance(meta, aujourdhui),
        "date_publication": champ(meta, "startDate")[:10],
        "description": f"{FAMILLES.get(famille, 'UE')}. Ref {reference}. "
                       + texte_brut(champ(meta, "description"))[:1200],
        "lien": resultat.get("url", ""),
    }


class UeFundingTendersScraper(BaseScraper):
    source_key = "ue_ft"
    nom = "UE Funding & Tenders"
    site = EU_FT_SITE

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        # Le portail laisse "ouverts" des avis echus depuis des annees : sans
        # echeance (viviers d'experts, marches permanents), on juge a la fraicheur.
        recent = (date.today() - timedelta(days=EU_FT_SANS_DATE_MAX_JOURS)).isoformat()
        champs = {"query": json.dumps(REQUETE), "languages": '["en"]',
                  "sort": '{"field":"startDate","order":"DESC"}'}
        nouveaux, vus = [], set(seen_ids)
        for page in range(1, EU_FT_MAX_PAGES + 1):
            if page > 1:
                time.sleep(EU_FT_PAGE_DELAY)
            try:
                resultats = post_multipart_json(EU_FT_URL, HEADERS, champs, params={
                    "apiKey": "SEDIA", "text": "***",
                    "pageSize": EU_FT_PAGE_SIZE, "pageNumber": page}).get("results") or []
            except Exception as exc:
                print(f"UE Funding & Tenders : page {page} en echec ({str(exc)[:60]}).")
                break
            for item in filter(None, (normalize(r, aujourdhui) for r in resultats)):
                # Un meme avis revient sous plusieurs langues : on garde le premier.
                ouvert = (item["date_limite"] >= aujourdhui if item["date_limite"]
                          else item["date_publication"] >= recent)
                if item["id"] not in vus and ouvert:
                    vus.add(item["id"])
                    nouveaux.append(item)
            if len(resultats) < EU_FT_PAGE_SIZE:
                break
        return nouveaux[:limite] if limite else nouveaux
