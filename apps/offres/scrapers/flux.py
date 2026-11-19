"""Sources publiees en flux RSS ou Atom.

Un flux rend titre, lien, date et resume. Chaque source precise ce qu'elle
sait en tirer (echeance, acheteur, pays) dans `completer`, et se declare en
quelques attributs (voir les classes en fin de module).
"""

import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime

from .base import BaseScraper
from .fid import texte_brut
from .http import get
from Offre.sources import (RELIEFWEB_RSS, URUGUAY_RSS, PLACSP_ATOM, FLUX_MAX_JOURS,
                           PLACSP_MAX_PAGES, AIIB_RSS, AIIB_PROJETS_RSS, FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0"}
ATOM = "{http://www.w3.org/2005/Atom}"


def date_flux(brut: str) -> str:
    """RFC 822 (RSS) ou ISO 8601 (Atom) -> "AAAA-MM-JJ", vide si illisible."""
    brut = (brut or "").strip()
    try:
        return parsedate_to_datetime(brut).date().isoformat()
    except (TypeError, ValueError):
        pass
    if re.match(r"\d{4}-\d{2}-\d{2}", brut):
        return brut[:10]
    try:                                         # "Nov 19, 2026" (AIIB)
        return datetime.strptime(brut, "%b %d, %Y").date().isoformat()
    except ValueError:
        return ""


def entrees(xml: bytes) -> tuple[list, str]:
    """(entrees, lien de la page suivante) d'un flux RSS ou Atom."""
    racine = ET.fromstring(xml)
    if racine.tag == ATOM + "feed":
        suivante = next((l.get("href") for l in racine.findall(ATOM + "link")
                         if l.get("rel") == "next"), "")
        return [{
            "titre": (e.findtext(ATOM + "title") or "").strip(),
            "lien": next((l.get("href") for l in e.findall(ATOM + "link")), ""),
            "guid": e.findtext(ATOM + "id") or "",
            "date": date_flux(e.findtext(ATOM + "updated")),
            "resume": e.findtext(ATOM + "summary") or "",
        } for e in racine.iter(ATOM + "entry")], suivante
    return [{
        "titre": (i.findtext("title") or "").strip(),
        "lien": (i.findtext("link") or "").strip(),
        "guid": i.findtext("guid") or i.findtext("link") or "",
        "date": date_flux(i.findtext("pubDate")),
        "resume": i.findtext("description") or "",
        "auteur": i.findtext("author") or "",
    } for i in racine.iter("item")], ""


class FluxScraper(BaseScraper):
    url: str = ""
    prefixe: str = ""
    organisation: str = ""
    pays: str = ""
    #: Flux pagine par lien "next" (Atom) : nombre de pages lues au plus.
    max_pages: int = 1

    def ident(self, entree: dict) -> str:
        return entree["guid"].rstrip("/").rsplit("/", 1)[-1]

    def completer(self, item: dict, entree: dict) -> dict | None:
        """Echeance, acheteur, pays tires du resume. None pour ecarter l'entree."""
        return item

    def normalize(self, entree: dict) -> dict | None:
        if not entree["titre"] or not entree["guid"]:
            return None
        resume = texte_brut(entree["resume"])
        return self.completer({
            "id": f"{self.prefixe}-{self.ident(entree)}",
            "source": self.source_key,
            "titre": entree["titre"],
            "organisation": self.organisation,
            "pays": self.pays,
            "date_limite": "",
            "date_publication": entree["date"],
            "description": resume[:1500],
            "lien": entree["lien"],
        }, {**entree, "texte": resume})

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        recent = (date.today() - timedelta(days=FLUX_MAX_JOURS)).isoformat()
        url, nouveaux, vus = self.url, [], set(seen_ids)
        for page in range(self.max_pages):
            if page:
                time.sleep(1)
            try:
                lues, url = entrees(get(url, HEADERS, timeout=90).content)
            except Exception as exc:
                print(f"{self.nom} : page {page + 1} en echec ({str(exc)[:60]}).")
                break
            for item in filter(None, map(self.normalize, lues)):
                ouvert = (item["date_limite"] >= aujourdhui if item["date_limite"]
                          else item["date_publication"] >= recent)
                if item["id"] not in vus and ouvert:
                    vus.add(item["id"])
                    nouveaux.append(item)
            # Flux du plus recent au plus ancien : passe la fenetre, on s'arrete.
            if not url or not lues or min(e["date"] for e in lues) < recent:
                break
        return nouveaux[:limite] if limite else nouveaux


class ReliefwebScraper(FluxScraper):
    """Offres d'emploi et de consultance humanitaires (ReliefWeb, OCHA)."""
    source_key = "reliefweb"
    nom = "ReliefWeb (emplois et consultances)"
    site = "https://reliefweb.int/jobs"
    url, prefixe = RELIEFWEB_RSS, "reliefweb"

    def ident(self, entree):
        m = re.search(r"/job/(\d+)", entree["guid"])
        return m.group(1) if m else super().ident(entree)

    def completer(self, item, entree):
        texte = entree["texte"]
        pays = re.search(r"Country:\s*(.+?)\s*Organization:", texte)
        cloture = re.search(r"Closing date:\s*(\d{1,2} \w{3} \d{4})", texte)
        item["organisation"] = entree.get("auteur", "")
        item["pays"] = pays.group(1) if pays else ""
        if cloture:
            item["date_limite"] = datetime.strptime(cloture.group(1), "%d %b %Y").date().isoformat()
        return item


class UruguayScraper(FluxScraper):
    """Achats publics de l'Uruguay (ARCE, comprasestatales.gub.uy)."""
    source_key = "uruguay"
    nom = "Uruguay (Compras Estatales)"
    site = "https://www.comprasestatales.gub.uy/consultas/"
    url, prefixe, pays = URUGUAY_RSS, "uy", "Uruguay"

    def completer(self, item, entree):
        # "Licitación Pública 29188/2027 - Administración Nacional de Puertos | ..."
        procedure, _, acheteur = entree["titre"].partition(" - ")
        objet = entree["texte"].split("Recepción de ofertas")[0].strip()
        cloture = re.search(r"Recepción de ofertas hasta:\s*(\d{2})/(\d{2})/(\d{4})", entree["texte"])
        item.update(titre=objet or entree["titre"], organisation=acheteur.split(" | ")[0],
                    description=f"{procedure}. {objet}")
        if cloture:
            item["date_limite"] = f"{cloture.group(3)}-{cloture.group(2)}-{cloture.group(1)}"
        return item


class EspagneScraper(FluxScraper):
    """Plateforme des marches publics de l'Etat espagnol (PLACSP), flux Atom."""
    source_key = "espagne"
    nom = "Espagne (PLACSP)"
    site = "https://contrataciondelestado.es/"
    url, prefixe, pays, max_pages = PLACSP_ATOM, "es", "Espagne", PLACSP_MAX_PAGES

    def completer(self, item, entree):
        # "Id licitación: X; Órgano de Contratación: Y; Importe: Z EUR; Estado: PUB"
        champs = dict(p.split(": ", 1) for p in entree["texte"].split("; ") if ": " in p)
        if champs.get("Estado") != "PUB":       # EV, ADJ, RES : en evaluation ou attribue
            return None
        item["organisation"] = champs.get("Órgano de Contratación", "")
        return item


class AiibScraper(FluxScraper):
    """AIIB : achats de la banque elle-meme (appels publies sur SAP Ariba)."""
    source_key = "aiib"
    nom = "AIIB (achats de la banque)"
    site = "https://www.aiib.org/en/opportunities/business/corporate-procurement/"
    url, prefixe, organisation, pays = AIIB_RSS, "aiib", "Asian Infrastructure Investment Bank", "Chine"
    groupe = "aiib"

    def ident(self, entree):
        # ".../RfxEvent/preview/1110030514?anId=ANONYMOUS" : pas de guid, l'evenement Ariba fait foi.
        m = re.search(r"/preview/(\d+)", entree["lien"])
        return m.group(1) if m else super().ident(entree)


class AiibProjetsScraper(FluxScraper):
    """AIIB : avis des projets qu'elle finance. Le flux melange avis, plans de
    passation (.xlsx) et attributions : on ne garde que les avis."""
    source_key = "aiib_projets"
    nom = "AIIB (projets finances)"
    site = "https://www.aiib.org/en/opportunities/business/project-procurement/"
    url, prefixe, groupe = AIIB_PROJETS_RSS, "aiibp", "aiib"

    def ident(self, entree):
        # Pas de guid ; le nom seul ("Bangladesh/REOI.pdf") se repete d'un projet a l'autre.
        return re.sub(r"^https?://[^/]+/", "", entree["lien"])[-200:]

    def completer(self, item, entree):
        lien = entree["lien"]
        if lien.endswith(".xlsx") or "Award" in lien:
            return None
        pays = re.search(r"/_download/([^/]+)/", lien)
        item["pays"] = pays.group(1).replace("-", " ") if pays else ""
        item["organisation"] = "Projet finance par l'AIIB"
        return item
