"""Organisations internationales dont la liste d'appels tient sur des pages HTML simples.

- ONU, Division des achats (UNPD) : manifestations d'interet du Secretariat.
  Chaque carte renvoie a sa fiche UNGM : on reprend l'identifiant "ungm-<n>"
  du scraper UNGM, pour qu'un meme avis ne soit jamais enregistre deux fois.
- OSCE : appels ouverts de ses missions (Europe de l'Est, Asie centrale).
- OPEC Fund : avis des projets qu'il finance (Afrique, Amerique latine, Asie).
- Cinquieme vague : Union africaine, Ravinala Airports (Madagascar), Unitaid,
  Pakistan (PPRA), Sierra Leone (NPPA).
"""

import re
import time
from datetime import date, datetime, timedelta

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import (UNPD_URL, UNPD_MAX_PAGES, OSCE_URL, OSCE_BASE, OSCE_MAX_PAGES,
                           OPEC_URL, UA_URL, RAVINALA_URL, UNITAID_URL, PAKISTAN_URL,
                           PAKISTAN_BASE, PAKISTAN_MAX_PAGES, SIERRA_LEONE_URL,
                           PAGES_SANS_DATE_MAX_JOURS, FIRST_RUN_MAX_ITEMS)

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


# --- Cinquieme vague (19/11/2026) ---

class UnionAfricaineScraper(PagesScraper):
    """Commission de l'Union africaine et ses organes : la page ne liste que les appels ouverts."""
    source_key = "union_africaine"
    nom = "Union africaine"
    site = UA_URL
    url = UA_URL

    def extraire(self, html):
        avis = []
        for ligne in BeautifulSoup(html, "html.parser").select("tbody tr"):
            lien = ligne.select_one(".views-field-title a[href]")
            dates = [t.get("datetime", "")[:10] for t in ligne.select("time[datetime]")]
            if not lien or len(dates) < 2:
                continue
            numero = texte(ligne.select_one(".views-field-field-text-bidnumber"))
            titre = texte(lien)
            avis.append({
                "id": "ua-" + lien["href"].rstrip("/").split("/bids/", 1)[-1][:200],
                "source": self.source_key, "titre": titre,
                "organisation": "Union africaine", "pays": "Ethiopie",
                "date_publication": dates[0], "date_limite": dates[1],
                "description": f"Ref {numero}. {titre}" if numero else titre,
                "lien": "https://au.int" + lien["href"],
            })
        return avis


class RavinalaScraper(PagesScraper):
    """Ravinala Airports, concessionnaire des aeroports d'Ivato et de Nosy Be."""
    source_key = "ravinala"
    nom = "Ravinala Airports (Madagascar)"
    site = RAVINALA_URL
    url = RAVINALA_URL

    def extraire(self, html):
        avis = []
        for carte in BeautifulSoup(html, "html.parser").select(".offer-card"):
            reference = texte(carte.select_one(".offer-card__upper-title"))
            titre = texte(carte.select_one(".offer-card__title"))
            if not reference or not titre:
                continue
            limite = re.search(r"(\d{2}/\d{2}/\d{4})", texte(carte.select_one(".offer-card__date")))
            lien = carte.select_one("a.offer-card__download[href]")
            avis.append({
                "id": f"ravinala-{reference}", "source": self.source_key, "titre": titre,
                "organisation": "Ravinala Airports", "pays": "Madagascar",
                "date_publication": "",
                "date_limite": date_texte(limite.group(1), "%d/%m/%Y") if limite else "",
                "description": f"{reference}. {texte(carte.select_one('.offer-card__descr'))[:1500]}",
                "lien": lien["href"] if lien else self.site,
            })
        return avis


class UnitaidScraper(PagesScraper):
    """Appels a propositions d'Unitaid (sante mondiale). Seule la premiere liste est ouverte."""
    source_key = "unitaid"
    nom = "Unitaid (appels a propositions)"
    site = UNITAID_URL
    url = UNITAID_URL

    def extraire(self, html):
        ouverts = BeautifulSoup(html, "html.parser").select_one(".open-proposal-list")
        avis = []
        for carte in ouverts.select(".cfp-row") if ouverts else []:
            lien = carte.select_one(".item-link a[href]")
            titre = texte(carte.select_one(".proposal-title")).rstrip("…")
            m = re.search(r"sf_id=(\w+)", lien["href"]) if lien else None
            if not m or not titre:
                continue
            # "Monday, 01 March 2027 at 12:00 CET"
            limite = re.search(r"\d{2} [A-Z][a-z]+ \d{4}", texte(carte.select_one(".proposal-date")))
            avis.append({
                "id": f"unitaid-{m.group(1)}", "source": self.source_key, "titre": titre,
                "organisation": "Unitaid", "pays": "",
                "date_publication": "",
                "date_limite": date_texte(limite.group(), "%d %B %Y") if limite else "",
                "description": f"Appel a propositions. {texte(carte.select_one('.proposal-description'))}",
                "lien": lien["href"],
            })
        return avis


class PakistanScraper(PagesScraper):
    """Pakistan, PPRA (EPMS) : appels actifs des organismes federaux."""
    source_key = "pakistan"
    nom = "Pakistan (PPRA)"
    site = PAKISTAN_URL
    url, premiere_page, max_pages = PAKISTAN_URL, 1, PAKISTAN_MAX_PAGES

    def extraire(self, html):
        avis = []
        for ligne in BeautifulSoup(html, "html.parser").select("tr.cb-rt-main"):
            numero = texte(ligne.select_one(".cb-rt-name"))
            details = ligne.select_one("td[data-label='Tender Details']")
            titre = texte(details.select_one("strong")) if details else ""
            if not numero or not titre:
                continue
            detail = ligne.find_next_sibling("tr")
            entite = ""
            if detail and "cb-rt-detail" in detail.get("class", []):
                entite = texte(detail.select_one(".cb-rt-dv strong"))
            precisions = " ".join(texte(x) for x in details.select("small"))
            lien = ligne.select_one("a[href*='tender-details']")
            avis.append({
                "id": f"pk-{numero}", "source": self.source_key, "titre": titre,
                "organisation": entite, "pays": "Pakistan",
                "date_publication": date_texte(texte(ligne.select_one("td[data-label='Advertised']")), "%b %d, %Y"),
                "date_limite": date_texte(texte(ligne.select_one("td[data-label='Closing'] strong")), "%b %d, %Y"),
                "description": f"{titre}. {precisions}"[:1500],
                "lien": PAKISTAN_BASE + lien["href"] if lien else self.site,
            })
        return avis


class SierraLeoneScraper(PagesScraper):
    """Sierra Leone, NPPA : tableau des appels en cours."""
    source_key = "sierra_leone"
    nom = "Sierra Leone (NPPA)"
    site = SIERRA_LEONE_URL
    url = SIERRA_LEONE_URL

    def extraire(self, html):
        avis = []
        for ligne in BeautifulSoup(html, "html.parser").select("tr"):
            cellules = [texte(td) for td in ligne.find_all("td")]
            lien = ligne.select_one("a[href]")
            if len(cellules) < 4 or not lien or not cellules[3]:
                continue
            entite, publie, cloture, titre = cellules[:4]
            avis.append({
                # Le PDF est propre a chaque avis ; l'intitule ("PROCUREMENT OF GOODS...") ne l'est pas.
                "id": "sl-" + lien["href"].rstrip("/").rsplit("/", 1)[-1][:200],
                "source": self.source_key, "titre": titre,
                "organisation": entite, "pays": "Sierra Leone",
                "date_publication": date_texte(publie, "%d-%m-%Y"),
                "date_limite": date_texte(cloture, "%d-%m-%Y"),
                "description": f"{entite}. {titre}",
                "lien": lien["href"],
            })
        return avis
