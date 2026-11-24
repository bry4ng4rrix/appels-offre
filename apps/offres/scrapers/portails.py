"""Portails publics a API JSON propre, sans format commun (ni OCDS ni RSS).

- Suisse, simap.ch : appels de la Confederation, des cantons et des communes.
- New York, City Record : appels de la ville (jeu de donnees Socrata).
- Sixieme vague : autres jeux Socrata (Los Angeles, Delaware, comte de
  Montgomery, Texas DOT, E-Rate), Toronto (CKAN), Pays-Bas (TenderNed),
  Roumanie (SICAP).
"""

import time
from datetime import date, timedelta

from .base import BaseScraper
from .fid import texte_brut
from .http import get_json, post_json
from Offre.sources import (SIMAP_URL, SIMAP_FICHE, SIMAP_FENETRE_JOURS, SIMAP_MAX_PAGES,
                           NYC_URL, NYC_FICHE, LA_URL, DELAWARE_URL, MONTGOMERY_URL, TXDOT_URL,
                           ERATE_URL, TORONTO_URL, TENDERNED_URL, TENDERNED_FENETRE_JOURS,
                           TENDERNED_MAX_PAGES, SICAP_URL, SICAP_FICHE, SICAP_MAX_PAGES,
                           FIRST_RUN_MAX_ITEMS)

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


def url_socrata(champ) -> str:
    """Champ "url" de Socrata : {"url": "..."} ou chaine."""
    return (champ or {}).get("url", "") if isinstance(champ, dict) else (champ or "")


class SocrataScraper(BaseScraper):
    """Jeu de donnees Socrata : une requete SoQL, une fonction de conversion par source."""
    url: str = ""
    ordre: str = ""
    limite_lignes: int = 1000
    #: Parametres SoQL supplementaires ($select, $group...).
    extra: dict = {}

    def filtre(self, aujourdhui: str) -> str:
        raise NotImplementedError

    def convertir(self, ligne: dict) -> dict | None:
        raise NotImplementedError

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        lignes = get_json(self.url, HEADERS, {
            "$limit": self.limite_lignes, "$order": self.ordre,
            "$where": self.filtre(date.today().isoformat()), **self.extra}, timeout=90)
        vus, nouveaux = set(seen_ids), []
        for item in filter(None, map(self.convertir, lignes)):
            if item["id"] not in vus:
                vus.add(item["id"])
                nouveaux.append(item)
        return nouveaux[:limite] if limite else nouveaux


class NewYorkScraper(SocrataScraper):
    source_key = "new_york"
    nom = "New York (City Record)"
    site = "https://a856-cityrecord.nyc.gov/"
    url, ordre = NYC_URL, "start_date DESC"

    def filtre(self, aujourdhui):
        return f"type_of_notice_description='Solicitation' AND due_date >= '{aujourdhui}'"

    def convertir(self, ligne):
        return normalize_nyc(ligne)


def _item(source, ident, titre, organisation, pays, publie, limite, description, lien):
    return {"id": ident, "source": source, "titre": titre.strip(), "organisation": organisation,
            "pays": pays, "date_publication": (publie or "")[:10], "date_limite": (limite or "")[:10],
            "description": description, "lien": lien}


class LosAngelesScraper(SocrataScraper):
    """Los Angeles (ville, comte et agences), portail RAMP."""
    source_key = "los_angeles"
    nom = "Los Angeles (RAMP)"
    site = "https://www.rampla.org/"
    url, ordre = LA_URL, "bidpost DESC"

    def filtre(self, aujourdhui):
        return f"stagename='Open' AND closedate >= '{aujourdhui}'"

    def convertir(self, l):
        if not l.get("rampid") or not l.get("title"):
            return None
        return _item(self.source_key, f"la-{l['rampid']}", l["title"], l.get("department", ""),
                     "États-Unis", l.get("bidpost"), l.get("closedate"),
                     ". ".join(x for x in (l.get("type"), l.get("category"), l["title"]) if x),
                     url_socrata(l.get("url")) or self.site)


class DelawareScraper(SocrataScraper):
    source_key = "delaware"
    nom = "Delaware (Etat, MyMarketplace)"
    site = "https://mmp.delaware.gov/"
    url, ordre = DELAWARE_URL, "opendate DESC"

    def filtre(self, aujourdhui):
        return f"deadlinedate >= '{aujourdhui}'"

    def convertir(self, l):
        if not l.get("contractnumber") or not l.get("contracttitle"):
            return None
        return _item(self.source_key, f"de-{l['contractnumber']}", l["contracttitle"],
                     f"Etat du Delaware ({l.get('agencycode', '')})", "États-Unis",
                     l.get("opendate"), l.get("deadlinedate"),
                     f"Contrat {l['contractnumber']}. {l['contracttitle']}",
                     url_socrata(l.get("bidurl")) or self.site)


class MontgomeryScraper(SocrataScraper):
    source_key = "montgomery"
    nom = "Comte de Montgomery (Maryland)"
    site = "https://www.montgomerycountymd.gov/PRO/"
    url, ordre = MONTGOMERY_URL, "issuancedate DESC"

    def filtre(self, aujourdhui):
        return f"closingdate >= '{aujourdhui}'"

    def convertir(self, l):
        if not l.get("number") or not l.get("description"):
            return None
        return _item(self.source_key, f"mcmd-{l['number']}", l["description"],
                     l.get("department", ""), "États-Unis", l.get("issuancedate"), l.get("closingdate"),
                     f"{l.get('type', '')} {l['number']}. {l['description']}".strip(),
                     url_socrata(l.get("bidtab")) or self.site)


TXDOT_CHAMPS = ("project_id,control_section_job_csj,county,district_division,highway,"
                "project_classification,proposal_published_date,bid_recieved_until_date_and,"
                "sealed_engineer_s_estimate")


class TexasDotScraper(SocrataScraper):
    """Texas, departement des transports : une ligne par poste de prix, regroupees par projet."""
    source_key = "texas_dot"
    nom = "Texas DOT (travaux routiers)"
    site = "https://www.txdot.gov/business/letting-bids.html"
    url, ordre = TXDOT_URL, "proposal_published_date DESC"
    extra = {"$select": TXDOT_CHAMPS, "$group": TXDOT_CHAMPS}

    def filtre(self, aujourdhui):
        return f"bid_recieved_until_date_and >= '{aujourdhui}'"

    def convertir(self, l):
        if not l.get("project_id"):
            return None
        titre = f"{l.get('project_classification', 'Travaux')} - {l.get('highway', '')}, comte de {l.get('county', '')}"
        estimation = l.get("sealed_engineer_s_estimate")
        return _item(self.source_key, f"txdot-{l['project_id']}", titre,
                     f"Texas DOT, district {l.get('district_division', '')}", "États-Unis",
                     l.get("proposal_published_date"), l.get("bid_recieved_until_date_and"),
                     f"CSJ {l.get('control_section_job_csj', '')}. {titre}."
                     + (f" Estimation : {float(estimation):,.0f} USD." if estimation else ""),
                     self.site)


class ErateScraper(SocrataScraper):
    """E-Rate : ecoles et bibliotheques americaines qui mettent en concurrence leurs services
    internet et reseau (formulaire 470 de l'USAC)."""
    source_key = "erate"
    nom = "E-Rate (ecoles et bibliotheques, USA)"
    site = "https://www.usac.org/e-rate/applicant-process/competitive-bidding/"
    url, ordre = ERATE_URL, "certified_datetime DESC"

    def filtre(self, aujourdhui):
        return f"f470_status='Certified' AND allowable_contract_date >= '{aujourdhui}'"

    def convertir(self, l):
        if not l.get("application_number") or not l.get("billed_entity_name"):
            return None
        lieu = ", ".join(x for x in (l.get("billed_entity_city"), l.get("billed_entity_state")) if x)
        besoin = " ".join(x for x in (l.get("category_one_description"), l.get("category_two_description")) if x)
        return _item(self.source_key, f"erate-{l['application_number']}",
                     f"Services internet et reseau : {l['billed_entity_name']} ({lieu})",
                     l["billed_entity_name"], "États-Unis",
                     l.get("certified_datetime"), l.get("allowable_contract_date"),
                     f"E-Rate, annee {l.get('funding_year', '')}. {besoin[:1200]}",
                     url_socrata(l.get("f470_number")) or self.site)


class TorontoScraper(BaseScraper):
    """Toronto : appels de la ville (jeu CKAN "Toronto Bids Solicitations")."""
    source_key = "toronto"
    nom = "Toronto (ville)"
    site = "https://www.toronto.ca/business-economy/doing-business-with-the-city/"

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        lignes = get_json(TORONTO_URL, HEADERS, timeout=60)["result"]["records"]
        nouveaux, vus = [], set(seen_ids)
        for l in lignes:
            numero, texte = l.get("Document Number"), " ".join((l.get("Solicitation Document Description") or "").split())
            if not numero or not texte or (l.get("Submission Deadline") or "") < aujourdhui:
                continue
            item = _item(self.source_key, f"to-{numero}", texte.split(". ")[0][:200],
                         f"Ville de Toronto, {l.get('Division', '')}", "Canada",
                         l.get("Issue Date"), l.get("Submission Deadline"),
                         f"{l.get('RFx (Solicitation) Type', '')} {numero}. {l.get('High Level Category', '')}. {texte[:1200]}",
                         self.site)
            # Un meme document peut figurer deux fois (deux lignes de categorie).
            if item["id"] not in vus:
                vus.add(item["id"])
                nouveaux.append(item)
        return nouveaux[:limite] if limite else nouveaux


class PaysBasScraper(BaseScraper):
    """Pays-Bas, TenderNed : avis de marche ("AAO") publies dans la fenetre."""
    source_key = "pays_bas"
    nom = "Pays-Bas (TenderNed)"
    site = "https://www.tenderned.nl/aankondigingen/overzicht"

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today().isoformat()
        depuis = (date.today() - timedelta(days=TENDERNED_FENETRE_JOURS)).isoformat()
        nouveaux, vus = [], set(seen_ids)
        for page in range(TENDERNED_MAX_PAGES):
            if page:
                time.sleep(1)
            try:
                lues = get_json(TENDERNED_URL, HEADERS, {"publicatieType": "AAO", "page": page,
                                                         "size": 100}).get("content") or []
            except Exception as exc:
                print(f"{self.nom} : page {page + 1} en echec ({str(exc)[:60]}).")
                break
            for p in lues:
                cloture = (p.get("sluitingsDatum") or "")[:10]
                item = _item(self.source_key, f"nl-{p.get('publicatieId')}", p.get("aanbestedingNaam") or "",
                             p.get("opdrachtgeverNaam", ""), "Pays-Bas", p.get("publicatieDatum"), cloture,
                             ". ".join(x for x in ((p.get("procedure") or {}).get("omschrijving"),
                                                   (p.get("typeOpdracht") or {}).get("omschrijving"),
                                                   (p.get("opdrachtBeschrijving") or "")[:1200]) if x),
                             (p.get("link") or {}).get("href") or self.site)
                if item["titre"] and cloture >= aujourdhui and item["id"] not in vus:
                    vus.add(item["id"])
                    nouveaux.append(item)
            if not lues or min(p.get("publicatieDatum") or "" for p in lues) < depuis:
                break
        return nouveaux[:limite] if limite else nouveaux


class RoumanieScraper(BaseScraper):
    """Roumanie, SICAP : avis de participation dont la remise des offres n'est pas passee."""
    source_key = "roumanie"
    nom = "Roumanie (SICAP)"
    site = "https://www.e-licitatie.ro/pub/notices/contract-notices/list/0/0"

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        entetes = {**HEADERS, "Referer": "https://www.e-licitatie.ro/"}
        nouveaux, vus = [], set(seen_ids)
        for page in range(SICAP_MAX_PAGES):
            if page:
                time.sleep(1)
            try:
                lues = post_json(SICAP_URL, entetes, {
                    "pageSize": 50, "pageIndex": page, "sysNoticeTypeIds": [2], "sortProperties": [],
                    "startTenderReceiptDeadline": date.today().isoformat() + "T00:00:00"}).get("items") or []
            except Exception as exc:
                print(f"{self.nom} : page {page + 1} en echec ({str(exc)[:60]}).")
                break
            for a in lues:
                acheteur = (a.get("contractingAuthorityNameAndFN") or "").split(" - ", 1)[-1]
                item = _item(self.source_key, f"ro-{a.get('cNoticeId')}", a.get("contractTitle") or "",
                             acheteur, "Roumanie", a.get("noticeStateDate"), a.get("maxTenderReceiptDeadline"),
                             ". ".join(x for x in (a.get("noticeNo"), (a.get("sysProcedureType") or {}).get("text"),
                                                   a.get("cpvCodeAndName"), a.get("estimatedValueExport")) if x),
                             SICAP_FICHE.format(a.get("cNoticeId")))
                if item["titre"] and item["id"] not in vus:
                    vus.add(item["id"])
                    nouveaux.append(item)
            if len(lues) < 50:
                break
        return nouveaux[:limite] if limite else nouveaux
