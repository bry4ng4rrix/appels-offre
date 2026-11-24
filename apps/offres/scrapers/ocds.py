"""Portails publies au standard OCDS (Open Contracting Data Standard).

Le format d'une "release" est commun : tender.title / description /
tenderPeriod.endDate, buyer.name, date. Seule l'enveloppe change d'un
portail a l'autre (curseur, page, record compile) : chaque source n'ecrit
que sa boucle de lecture.
"""

import re
import time
from datetime import date, timedelta

from .base import BaseScraper
from .http import get_json
from Offre.sources import (CF_URL, FTS_URL, PE_URL, PY_URL, PY_FICHE, SEAO_CKAN, OCDS_MAX_PAGES,
                           OCDS_FENETRE_JOURS, FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "application/json"}


class OcdsScraper(BaseScraper):
    prefixe: str = ""
    pays: str = ""
    #: Le Perou met la date de publication dans tenderPeriod.endDate.
    echeance_fiable: bool = True

    def lien(self, release: dict) -> str:
        docs = (release.get("tender") or {}).get("documents") or []
        return next((d["url"] for d in docs if d.get("url")), self.site)

    def normalize(self, release: dict) -> dict | None:
        t = release.get("tender") or {}
        titre, description = (t.get("title") or "").strip(), (t.get("description") or "").strip()
        if not release.get("ocid") or not (titre or description):
            return None
        # "CP-ABR-2-2026-DREA/CS-2" : une reference, pas un intitule.
        if description and " " not in titre:
            titre, description = description[:300], f"Ref {titre}. {description}"
        methode = t.get("procurementMethodDetails") or t.get("procurementMethod") or ""
        return {
            "id": f"{self.prefixe}-{release['ocid']}",
            "source": self.source_key,
            "titre": titre,
            "organisation": (release.get("buyer") or {}).get("name", ""),
            "pays": self.pays,
            "date_limite": ((t.get("tenderPeriod") or {}).get("endDate") or "")[:10]
                           if self.echeance_fiable else "",
            "date_publication": (release.get("date") or "")[:10],
            "description": ". ".join(x for x in (methode, description[:1500]) if x),
            "lien": self.lien(release),
        }

    def releases(self, page: int, curseur: str) -> tuple[list, str]:
        """(releases d'une page, curseur de la suivante ou "")."""
        raise NotImplementedError

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        recent = (date.today() - timedelta(days=OCDS_FENETRE_JOURS)).isoformat()
        nouveaux, vus, curseur = [], set(seen_ids), ""
        for page in range(1, OCDS_MAX_PAGES + 1):
            if page > 1:
                time.sleep(1)
            try:
                lues, curseur = self.releases(page, curseur)
            except Exception as exc:
                print(f"{self.nom} : page {page} en echec ({str(exc)[:60]}).")
                break
            items = list(filter(None, map(self.normalize, lues)))
            for item in items:
                ouvert = (item["date_limite"] >= aujourdhui if item["date_limite"]
                          else item["date_publication"] >= recent)
                if item["id"] not in vus and ouvert:
                    vus.add(item["id"])
                    nouveaux.append(item)
            # Pages du plus recent au plus ancien : passe la fenetre, on s'arrete.
            if not curseur or not items or min(i["date_publication"] for i in items) < recent:
                break
        return nouveaux[:limite] if limite else nouveaux


class ContractsFinderScraper(OcdsScraper):
    """Royaume-Uni, Contracts Finder (marches sous les seuils de Find a Tender)."""
    source_key = "royaume_uni"
    nom = "Royaume-Uni (Contracts Finder)"
    site = "https://www.contractsfinder.service.gov.uk/Search"
    prefixe, pays = "uk", "Royaume-Uni"

    def lien(self, release):
        return next((d["url"] for d in (release.get("tender") or {}).get("documents") or []
                     if d.get("documentType") == "tenderNotice"), self.site)

    def normalize(self, release):
        if (release.get("tender") or {}).get("status") != "active":
            return None
        return super().normalize(release)

    def releases(self, page, curseur):
        if curseur:
            reponse = get_json(curseur, HEADERS)
        else:
            depuis = (date.today() - timedelta(days=OCDS_FENETRE_JOURS)).isoformat()
            reponse = get_json(CF_URL, HEADERS, {"stages": "tender", "limit": 100,
                                                 "publishedFrom": depuis + "T00:00:00"})
        return reponse.get("releases") or [], (reponse.get("links") or {}).get("next", "")


class PerouScraper(OcdsScraper):
    """Perou, SEACE (OECE), API OCDS : 20 releases par page, les plus recentes d'abord."""
    source_key = "perou"
    nom = "Pérou (SEACE)"
    site = "https://contratacionesabiertas.oece.gob.pe/"
    prefixe, pays, echeance_fiable = "pe", "Pérou", False

    def releases(self, page, curseur):
        reponse = get_json(PE_URL, HEADERS, {"page": page})
        return reponse.get("releases") or [], (reponse.get("links") or {}).get("next") or ""


class ParaguayScraper(OcdsScraper):
    """Paraguay, DNCP : processus en "Convocatoria", chacun avec sa release compilee."""
    source_key = "paraguay"
    nom = "Paraguay (DNCP)"
    site = "https://www.contrataciones.gov.py/buscador/licitaciones.html"
    prefixe, pays = "py", "Paraguay"

    def lien(self, release):
        m = re.search(r"-(\d+)-\d+$", release.get("ocid", ""))
        return PY_FICHE.format(m.group(1)) if m else self.site

    def releases(self, page, curseur):
        reponse = get_json(PY_URL, HEADERS, {"tender.statusDetails": "Convocatoria", "page": page})
        pagination = reponse.get("pagination") or {}
        suite = "oui" if page < pagination.get("total_pages", 0) else ""
        return [r["compiledRelease"] for r in reponse.get("records") or []
                if r.get("compiledRelease")], suite


class QuebecScraper(OcdsScraper):
    """Quebec, SEAO : l'export hebdomadaire le plus recent publie sur Donnees Quebec.

    Une page unique : les avis initiaux (tag "tender") de la semaine, encore
    ouverts. Les modificatifs ("tenderUpdate") ne sont pas de nouveaux avis.
    """
    source_key = "quebec"
    nom = "Québec (SEAO)"
    site = "https://seao.gouv.qc.ca/"
    prefixe, pays = "qc", "Canada"

    def releases(self, page, curseur):
        ressources = get_json(SEAO_CKAN, HEADERS)["result"]["resources"]
        # Noms "hebdo_AAAAMMJJ_AAAAMMJJ.json" : l'ordre alphabetique est chronologique.
        hebdo = max((r for r in ressources if r.get("name", "").startswith("hebdo_")),
                    key=lambda r: r["name"])
        export = get_json(hebdo["url"], HEADERS, timeout=180)
        return [r for r in export.get("releases") or [] if "tender" in (r.get("tag") or [])], ""


class FindATenderScraper(ContractsFinderScraper):
    """Royaume-Uni, Find a Tender : marches au-dessus des seuils (Contracts Finder : en dessous)."""
    source_key = "find_a_tender"
    nom = "Royaume-Uni (Find a Tender)"
    site = "https://www.find-tender.service.gov.uk/"
    prefixe = "fts"

    def lien(self, release):
        return f"https://www.find-tender.service.gov.uk/Notice/{release.get('id', '')}"

    def releases(self, page, curseur):
        if curseur:
            reponse = get_json(curseur, HEADERS, timeout=60)
        else:
            depuis = (date.today() - timedelta(days=OCDS_FENETRE_JOURS)).isoformat()
            reponse = get_json(FTS_URL, HEADERS, {"stages": "tender", "limit": 100,
                                                  "updatedFrom": depuis + "T00:00:00"}, timeout=60)
        return reponse.get("releases") or [], (reponse.get("links") or {}).get("next", "")
