"""Marches publics d'Enabel (agence belge de cooperation, surtout en Afrique).

Source : API REST WordPress, type "tenders", puis la fiche de chaque nouvel
avis : l'echeance ("Date de cloture : 15 December 2026 10:00"), le pays et
le statut n'y figurent qu'en paragraphes <p><strong>Libelle :</strong> valeur.
"""

import re
import time
from datetime import date, datetime, timedelta

from bs4 import BeautifulSoup

from .base import BaseScraper
from .fid import texte_brut
from .http import get_html, get_json
from Offre.sources import (ENABEL_API, ENABEL_MAX_JOURS, ENABEL_MAX_PAGES,
                           ENABEL_PAGE_DELAY, FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0"}


def champs_fiche(html: str) -> dict:
    """{"pays": "RD Congo", "date de cloture": "15 December 2026 10:00", ...}"""
    champs = {}
    for gras in BeautifulSoup(html, "html.parser").select("p > strong"):
        libelle = gras.get_text(" ", strip=True).rstrip(" :").lower()
        valeur = " ".join(gras.parent.get_text(" ").split())
        champs[libelle] = valeur.split(":", 1)[-1].strip()
    return champs


def date_longue(brut: str) -> str:
    m = re.match(r"\d{1,2} [A-Za-z]+ \d{4}", brut or "")
    try:
        return datetime.strptime(m.group(), "%d %B %Y").date().isoformat() if m else ""
    except ValueError:
        return ""


def normalize(article: dict, champs: dict) -> dict | None:
    titre = texte_brut((article.get("title") or {}).get("rendered", ""))
    if not titre or champs.get("status", "").lower() not in ("ouvert", "open", ""):
        return None
    pays = champs.get("pays", "")
    return {
        "id": f"enabel-{article['id']}",
        "source": "enabel",
        "titre": titre,
        "organisation": "Enabel (cooperation belge)",
        "pays": pays,
        "date_limite": date_longue(champs.get("date de clôture", "")),
        "date_publication": (article.get("date") or "")[:10],
        "description": f"Marche public Enabel. Pays : {pays}. {titre}" if pays else titre,
        "lien": article.get("link", ""),
    }


class EnabelScraper(BaseScraper):
    source_key = "enabel"
    nom = "Enabel (Belgique)"
    site = "https://www.enabel.be/fr/liste-marches-publics/"

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        depuis = (date.today() - timedelta(days=ENABEL_MAX_JOURS)).isoformat()
        nouveaux = []
        for page in range(1, ENABEL_MAX_PAGES + 1):
            try:
                articles = get_json(ENABEL_API, HEADERS, {
                    "per_page": 100, "page": page, "after": depuis + "T00:00:00",
                    "_fields": "id,date,link,title"})
            except Exception as exc:
                if "400" not in str(exc):          # 400 = au-dela de la derniere page
                    print(f"Enabel : page {page} en echec ({str(exc)[:60]}).")
                break
            for article in articles:
                if f"enabel-{article['id']}" in seen_ids:
                    continue
                time.sleep(ENABEL_PAGE_DELAY)
                try:
                    champs = champs_fiche(get_html(article["link"], HEADERS))
                except Exception as exc:
                    print(f"  Enabel : fiche {article['id']} en echec ({str(exc)[:60]}).")
                    continue
                item = normalize(article, champs)
                if item and (not item["date_limite"] or item["date_limite"] >= aujourdhui):
                    nouveaux.append(item)
                    if limite and len(nouveaux) >= limite:
                        return nouveaux
            if len(articles) < 100:
                break
        return nouveaux
