"""Appels d'offres publies par des ONG internationales sur leur propre site.

Chaque page a sa mise en forme ; la logique commune (pagination, echeance,
fraicheur des avis sans date) est celle de PagesScraper.
"""

import hashlib
import re
from datetime import date

from bs4 import BeautifulSoup

from .organisations import PagesScraper, date_libre, date_texte, texte
from Offre.sources import (NRC_URL, GOAL_URL, PLAN_URL, ISLAMIC_RELIEF_URL, SFA_URL, DRC_URL,
                           WHH_URL, HI_URL, IRC_URL, MEDAIR_URL, ONG_SANS_DATE_MAX_JOURS)


def empreinte(titre: str) -> str:
    """Identifiant stable d'un avis qui n'en publie pas."""
    return hashlib.md5(titre.lower().encode()).hexdigest()[:12]


def slug(href: str) -> str:
    return href.strip().rstrip("/").rsplit("/", 1)[-1][:150]


def item(source, ident, titre, organisation, pays, publie, limite, description, lien):
    return {"id": ident, "source": source, "titre": titre, "organisation": organisation, "pays": pays,
            "date_publication": publie, "date_limite": limite, "description": description, "lien": lien}


class NrcScraper(PagesScraper):
    source_key = "nrc"
    nom = "NRC, Conseil norvegien pour les refugies"
    site = url = NRC_URL
    sans_date_max_jours = ONG_SANS_DATE_MAX_JOURS

    def extraire(self, html):
        avis = []
        for lien in BeautifulSoup(html, "html.parser").select("a[href^='/tender/']"):
            titre = texte(lien.select_one("h2"))
            if not titre:
                continue
            avis.append(item(self.source_key, f"nrc-{slug(lien['href'])}", titre,
                             "Norwegian Refugee Council", "",
                             date_texte(texte(lien.select_one("time")), "%d. %b %Y"), "", titre,
                             "https://www.nrc.no" + lien["href"]))
        return avis


class GoalScraper(PagesScraper):
    source_key = "goal"
    nom = "GOAL (ONG irlandaise)"
    site = url = GOAL_URL

    def extraire(self, html):
        avis = []
        for bloc in BeautifulSoup(html, "html.parser").select(".fl-accordion-item"):
            titre = texte(bloc.select_one(".fl-accordion-button-label"))
            contenu = texte(bloc.select_one(".fl-accordion-content")) or texte(bloc)
            if not titre:
                continue
            ref = re.search(r"Reference:\s*([A-Z0-9][A-Z0-9-]+)", contenu)
            cloture = re.search(r"(?i)receipt of offers", contenu)
            publie = re.search(r"(?i)publication", contenu)
            pays = bloc.find_previous("span", class_="fl-heading-text")
            avis.append(item(self.source_key, f"goal-{ref.group(1) if ref else empreinte(titre)}", titre,
                             texte(pays) or "GOAL", "",
                             date_libre(contenu[publie.end():publie.end() + 60]) if publie else "",
                             date_libre(contenu[cloture.end():cloture.end() + 80]) if cloture else "",
                             contenu[:1500], self.site))
        return avis


class PlanInternationalScraper(PagesScraper):
    source_key = "plan_international"
    nom = "Plan International"
    site = url = PLAN_URL

    def extraire(self, html):
        avis = []
        for titre_h3 in BeautifulSoup(html, "html.parser").select("h3.wp-block-heading"):
            titre = texte(titre_h3)
            if len(titre) < 15:
                continue
            corps = []
            for frere in titre_h3.find_next_siblings():
                if frere.name == "h3":
                    break
                corps.append(texte(frere))
            corps = " ".join(corps)
            delai = re.search(r"(?i)no later than", corps)
            bureau = re.search(r"Plan International ([A-Z][\w ]{2,30}?) is inviting", corps)
            avis.append(item(self.source_key, f"plan-{empreinte(titre)}", titre,
                             f"Plan International {bureau.group(1)}" if bureau else "Plan International",
                             bureau.group(1) if bureau else "", "",
                             date_libre(corps[delai.end():delai.end() + 80]) if delai else "",
                             corps[:1500], self.site))
        return avis


class IslamicReliefScraper(PagesScraper):
    source_key = "islamic_relief"
    nom = "Islamic Relief Worldwide"
    site = url = ISLAMIC_RELIEF_URL

    def extraire(self, html):
        avis, aujourdhui = [], date.today()
        for ligne in BeautifulSoup(html, "html.parser").select("div.tenders"):
            lien = ligne.select_one("a[href*='/tenders/']")
            colonnes = ligne.find_all("div", recursive=False)
            if not lien or len(colonnes) < 3 or texte(colonnes[2]) != "Open":
                continue
            # "17 Nov" sans annee : l'annee en cours, ou la precedente si la date serait future.
            publie = date_texte(f"{texte(colonnes[0])} {aujourdhui.year}", "%d %b %Y")
            if publie > aujourdhui.isoformat():
                publie = date_texte(f"{texte(colonnes[0])} {aujourdhui.year - 1}", "%d %b %Y")
            titre = texte(lien)
            avis.append(item(self.source_key, f"ir-{slug(lien['href'])}", titre, "Islamic Relief",
                             texte(colonnes[3]) if len(colonnes) > 3 else "", publie,
                             date_libre(texte(colonnes[4])) if len(colonnes) > 4 else "", titre, lien["href"]))
        return avis


class ScienceForAfricaScraper(PagesScraper):
    source_key = "science_for_africa"
    nom = "Science for Africa Foundation"
    site = url = SFA_URL

    def extraire(self, html):
        avis = []
        for lien in BeautifulSoup(html, "html.parser").select("a.clickable-title[href]"):
            titre = texte(lien)
            bloc = lien.parent
            limite = bloc.select_one("time[datetime]")
            avis.append(item(self.source_key, f"sfa-{slug(lien['href'])}", titre,
                             "Science for Africa Foundation", "Kenya", "",
                             limite["datetime"][:10] if limite else "", texte(bloc)[:1500],
                             "https://scienceforafrica.foundation" + lien["href"].strip()))
        return avis


class DrcScraper(PagesScraper):
    source_key = "drc"
    nom = "DRC, Conseil danois pour les refugies"
    site = url = DRC_URL

    def extraire(self, html):
        avis = []
        for art in BeautifulSoup(html, "html.parser").select("article.tenderList__item"):
            lien = art.select_one("a[href]")
            if not lien or art.get("data-status") == "archived":
                continue
            lieu = art.get("data-country", "")
            titre = texte(art.select_one(".tenderList__item__title"))
            d = lambda cle: (art.get(cle) or "")
            iso = lambda v: f"{v[:4]}-{v[4:6]}-{v[6:8]}" if len(v) == 8 else ""
            avis.append(item(self.source_key, f"drc-{slug(lien['href'])}", titre,
                             "Danish Refugee Council", lieu.rsplit("|", 1)[-1].strip().title(),
                             iso(d("data-published")), iso(d("data-deadline")),
                             f"{texte(art.select_one('.tenderList__item__country'))}. {titre}",
                             "https://drc.ngo" + lien["href"]))
        return avis


class WelthungerhilfeScraper(PagesScraper):
    source_key = "welthungerhilfe"
    nom = "Welthungerhilfe"
    site = url = WHH_URL

    def extraire(self, html):
        avis = []
        for bloc in BeautifulSoup(html, "html.parser").select(".tender__list__item"):
            lien = bloc.select_one(".tender__list__item__title a[href]")
            if not lien:
                continue
            ident = re.search(r"PID=(\d+)", lien["href"])
            date_de = lambda cls: (re.search(r"(\d{2}\.\d{2}\.\d{4})", texte(bloc.select_one(cls))) or [None, ""])[1]
            client = texte(bloc.select_one(".tender__list__item__client")).replace("Contracting Authority:", "").strip()
            titre = texte(lien)
            avis.append(item(self.source_key, f"whh-{ident.group(1) if ident else empreinte(titre)}", titre,
                             client, client.split(",")[-1].replace("Welthungerhilfe", "").strip(),
                             date_texte(date_de(".tender__list__item__date"), "%d.%m.%Y"),
                             date_texte(date_de(".tender__list__item__deadline"), "%d.%m.%Y"),
                             f"{client}. {titre}", lien["href"]))
        return avis


class HandicapInternationalScraper(PagesScraper):
    """Humanite & Inclusion : le sommaire de la page renvoie a chaque appel par une ancre
    "#AAMMJJ" (date de mise en ligne)."""
    source_key = "hi"
    nom = "Humanite & Inclusion (HI)"
    site = url = HI_URL
    sans_date_max_jours = ONG_SANS_DATE_MAX_JOURS

    def extraire(self, html):
        avis = []
        for lien in BeautifulSoup(html, "html.parser").select("a[href*='appels-d-offres#']"):
            ancre = lien["href"].split("#", 1)[1]
            titre = texte(lien.parent) or texte(lien)
            m = re.match(r"(\d{2})(\d{2})(\d{2})", ancre)
            if not m or len(titre) < 10:
                continue
            avis.append(item(self.source_key, f"hi-{ancre}", titre, "Humanite & Inclusion", "",
                             f"20{m.group(1)}-{m.group(2)}-{m.group(3)}", "", titre,
                             f"https://www.hi.org/fr/appels-d-offres#{ancre}"))
        return avis


class IrcScraper(PagesScraper):
    source_key = "irc"
    nom = "IRC, International Rescue Committee"
    site = url = IRC_URL
    sans_date_max_jours = ONG_SANS_DATE_MAX_JOURS

    def extraire(self, html):
        avis = []
        for carte in BeautifulSoup(html, "html.parser").select(".rplc-teaser-basic"):
            lien = carte.select_one("a[href]")
            titre = texte(carte.select_one(".rplc-teaser-basic__title"))
            if not lien or not titre:
                continue
            avis.append(item(self.source_key, f"irc-{slug(lien['href'])}", titre,
                             "International Rescue Committee", "",
                             date_libre(texte(carte.select_one(".rplc-teaser-basic__date"))), "", titre,
                             "https://www.rescue.org" + lien["href"].strip()))
        return avis


class MedairScraper(PagesScraper):
    source_key = "medair"
    nom = "Medair"
    site = url = MEDAIR_URL

    def extraire(self, html):
        avis = []
        for carte in BeautifulSoup(html, "html.parser").select(".card_tender_wrap"):
            champ = lambda nom: [texte(p) for p in carte.select(f"[fs-cmsfilter-field='{nom}']")]
            titre = " ".join(champ("name"))
            ref = [r for r in champ("ref") if r != "Ref:"]
            lien = carte.select_one("a.button[href]")
            if not titre or not lien:
                continue
            pays = " ".join(champ("country")) or " ".join(champ("location")).strip(" ,")
            avis.append(item(self.source_key, f"medair-{ref[0] if ref else slug(lien['href'])}", titre,
                             "Medair", pays, "", date_libre(" ".join(champ("deadline"))),
                             f"{' '.join(champ('category'))}. Ref {ref[0] if ref else ''}. {titre}",
                             "https://www.medair.org" + lien["href"]))
        return avis
