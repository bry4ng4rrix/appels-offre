"""Organisations internationales dont la liste d'appels tient sur des pages HTML simples.

- ONU, Division des achats (UNPD) : manifestations d'interet du Secretariat.
  Chaque carte renvoie a sa fiche UNGM : on reprend l'identifiant "ungm-<n>"
  du scraper UNGM, pour qu'un meme avis ne soit jamais enregistre deux fois.
- OSCE : appels ouverts de ses missions (Europe de l'Est, Asie centrale).
- OPEC Fund : avis des projets qu'il finance (Afrique, Amerique latine, Asie).
"""

import re
import time
from datetime import date, datetime, timedelta

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import (UNPD_URL, UNPD_MAX_PAGES, OSCE_URL, OSCE_BASE, OSCE_MAX_PAGES,
                           OPEC_URL, PAGES_SANS_DATE_MAX_JOURS, FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0"}


def texte(el) -> str:
    return " ".join(el.get_text(" ").split()) if el else ""


def date_texte(brut: str, *formats) -> str:
    for f in formats:
        try:
            return datetime.strptime(brut.strip(), f).date().isoformat()
        except ValueError:
            pass
    return ""


class PagesScraper(BaseScraper):
    """Liste paginee : `extraire(html)` rend les avis d'une page."""
    url: str = ""
    param_page: str = "page"
    premiere_page: int = 0
    max_pages: int = 1

    def extraire(self, html: str) -> list:
        raise NotImplementedError

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        # Sans echeance (avis generaux de l'OPEC Fund : "N/A"), on juge a la fraicheur.
        recent = (date.today() - timedelta(days=PAGES_SANS_DATE_MAX_JOURS)).isoformat()
        nouveaux, vus = [], set(seen_ids)
        for n in range(self.premiere_page, self.premiere_page + self.max_pages):
            if n > self.premiere_page:
                time.sleep(1)
            try:
                avis = self.extraire(get_html(self.url, HEADERS, {self.param_page: n} if n else None))
            except Exception as exc:
                print(f"{self.nom} : page {n} en echec ({str(exc)[:60]}).")
                break
            for item in avis:
                ouvert = (item["date_limite"] >= aujourdhui if item["date_limite"]
                          else item["date_publication"] >= recent)
                if item["id"] not in vus and ouvert:
                    vus.add(item["id"])
                    nouveaux.append(item)
            if not avis:
                break
        return nouveaux[:limite] if limite else nouveaux


class OnuAchatsScraper(PagesScraper):
    source_key = "onu_achats"
    nom = "ONU, Division des achats"
    site = UNPD_URL
    url, param_page, premiere_page, max_pages = UNPD_URL, "pg", 1, UNPD_MAX_PAGES

    def extraire(self, html):
        avis = []
        for carte in BeautifulSoup(html, "html.parser").select("li.views-row"):
            ungm = carte.select_one("a[href*='ungm.org/Public/Notice/']")
            m = re.search(r"/Notice/(\d+)", ungm["href"]) if ungm else None
            titre = texte(carte.select_one(".custom-card-title-field"))
            if not m or not titre:
                continue
            reference = texte(carte.select_one(".custom-card-title"))
            categorie = texte(carte.select_one(".eoi-commodity-group-field .field-content"))
            avis.append({
                "id": f"ungm-{m.group(1)}", "source": self.source_key, "titre": titre,
                "organisation": "Nations unies (Secretariat)", "pays": "",
                "date_publication": date_texte(texte(carte.select_one(".start")), "%d %b %Y"),
                "date_limite": date_texte(texte(carte.select_one(".end")), "%d %b %Y"),
                "description": f"Manifestation d'interet {reference}. Categorie : {categorie}. {titre}",
                "lien": ungm["href"],
            })
        return avis


class OsceScraper(PagesScraper):
    source_key = "osce"
    nom = "OSCE"
    site = OSCE_URL
    url, max_pages = OSCE_URL, OSCE_MAX_PAGES

    def extraire(self, html):
        avis = []
        for article in BeautifulSoup(html, "html.parser").select("article.node--type-tender"):
            lien = article.select_one("h4 a[href]")
            if not lien:
                continue
            champs = {texte(dt): dt.find_next_sibling("dd") for dt in article.select("dt")}
            heure = lambda cle: ((champs.get(cle) and champs[cle].select_one("time[datetime]")) or {}).get("datetime", "")[:10]
            entite = texte(champs.get("On behalf of"))
            titre = texte(lien)
            avis.append({
                "id": "osce-" + lien["href"].rstrip("/").rsplit("/", 1)[-1][:200],
                "source": self.source_key, "titre": titre,
                "organisation": entite or "OSCE", "pays": "",
                "date_publication": heure("Launch date"), "date_limite": heure("Deadline"),
                "description": f"Pour le compte de : {entite}. {titre}" if entite else titre,
                "lien": OSCE_BASE + lien["href"],
            })
        return avis


class OpecFundScraper(PagesScraper):
    source_key = "opec_fund"
    nom = "OPEC Fund (projets)"
    site = OPEC_URL
    url = OPEC_URL

    def extraire(self, html):
        avis = []
        for ligne in BeautifulSoup(html, "html.parser").select("tr"):
            cellules = ligne.find_all("td")
            lien = ligne.select_one("a[href]")
            if len(cellules) < 6 or not lien:
                continue
            publie, pays, titre, secteur, cloture, genre = (texte(c) for c in cellules[:6])
            m = re.search(r"/view/(\d+)", lien["href"])
            # "April 21, 2027 at 11:59 PM,(Costa Rica time)" : on ne garde que la date.
            cloture = re.search(r"[A-Z][a-z]+ \d{1,2}, \d{4}", cloture)
            avis.append({
                "id": f"opec-{m.group(1) if m else lien['href'][-60:]}",
                "source": self.source_key, "titre": titre,
                "organisation": "OPEC Fund (projet finance)", "pays": pays,
                "date_publication": date_texte(publie, "%B %d, %Y"),
                "date_limite": date_texte(cloture.group(), "%B %d, %Y") if cloture else "",
                "description": f"{genre}. Secteur : {secteur}. {titre}",
                "lien": lien["href"],
            })
        return avis
