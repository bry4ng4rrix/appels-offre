"""Portails nationaux ou regionaux publies en pages HTML (sixieme vague).

- Australie : Victoria et Territoire de la capitale (meme plateforme), Australie-Occidentale.
- Afrique : Eswatini (ESPPRA), Congo (ARMP), Mozambique (UFSA).
- Haiti : Commission nationale des marches publics.
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .organisations import PagesScraper, date_libre, date_texte, texte
from Offre.sources import (VICTORIA_URL, ACT_URL, TENDERS_AU_MAX_PAGES, WA_URL, ESWATINI_URL,
                           CONGO_URL, HAITI_URL, MOZAMBIQUE_URL, ONG_SANS_DATE_MAX_JOURS)


# Appels fictifs laisses en ligne pour s'entrainer a deposer une offre.
EXERCICE = re.compile(r"\b(demonstration tender|practice)\b", re.I)


def item(source, ident, titre, organisation, pays, publie, limite, description, lien):
    return {"id": ident, "source": source, "titre": titre, "organisation": organisation, "pays": pays,
            "date_publication": publie, "date_limite": limite, "description": description, "lien": lien}


class TendersAuScraper(PagesScraper):
    """Plateforme "Tenders" des Etats australiens (Victoria, ACT) : appels ouverts, 25 par page."""
    param_page, premiere_page, max_pages = "page", 1, TENDERS_AU_MAX_PAGES
    prefixe: str = ""
    etat: str = ""

    def extraire(self, html):
        avis = []
        for ligne in BeautifulSoup(html, "html.parser").select("tr[data-tender-code]"):
            lien = ligne.select_one("a.tenderRowTitle[href]")
            if not lien:
                continue
            code = ligne["data-tender-code"]
            details = [texte(x) for x in ligne.select(".line-item-detail")]
            emetteur = next((d.split(":", 1)[1].strip() for d in details if d.startswith("Issued by")), "")
            titre = texte(lien)
            if EXERCICE.search(titre):
                continue
            avis.append(item(self.source_key, f"{self.prefixe}-{code}", titre, emetteur or self.etat,
                             "Australie", date_libre(texte(ligne.select_one(".opening_date"))),
                             date_libre(texte(ligne.select_one(".closing_date"))),
                             f"{self.etat}. {texte(ligne.select_one('.tender-code-state'))}. "
                             f"{' '.join(details)}. {titre}", urljoin(self.url, lien["href"])))
        return avis


class VictoriaScraper(TendersAuScraper):
    source_key = "victoria"
    nom = "Australie, Victoria"
    site = url = VICTORIA_URL
    prefixe, etat = "vic", "Etat de Victoria"


class ActScraper(TendersAuScraper):
    source_key = "act_australie"
    nom = "Australie, Territoire de la capitale (ACT)"
    site = url = ACT_URL
    prefixe, etat = "act", "Territoire de la capitale australienne"


class AustralieOccidentaleScraper(PagesScraper):
    source_key = "australie_occidentale"
    nom = "Australie-Occidentale (Tenders WA)"
    site = url = WA_URL

    def extraire(self, html):
        avis = []
        for ligne in BeautifulSoup(html, "html.parser").select("tbody tr"):
            lien = ligne.select_one("a[href*='tender-details']")
            code = texte(ligne.select_one("td.left b"))
            if not lien or not code:
                continue
            resume = texte(ligne.select_one(".SUMMARY_SMALL"))
            cloture = re.search(r"(\d{1,2}) (\w{3}), (\d{4})", texte(ligne.select_one(".SUMMARY_CLOSINGDATE")))
            ident = re.search(r"id=(\d+)", lien["href"])
            titre = texte(lien)
            if EXERCICE.search(titre):
                continue
            avis.append(item(self.source_key, f"wa-{ident.group(1) if ident else code}", titre,
                             resume.split("UNSPSC")[0].replace("Issued by", "").strip(), "Australie", "",
                             date_texte(" ".join(cloture.groups()), "%d %b %Y") if cloture else "",
                             f"{code}. {resume}. {titre}",
                             "https://www.tenders.wa.gov.au" + lien["href"].split("&returnUrl")[0]))
        return avis


class EswatiniScraper(PagesScraper):
    source_key = "eswatini"
    nom = "Eswatini (ESPPRA)"
    site = url = ESWATINI_URL

    def extraire(self, html):
        avis = []
        for bloc in BeautifulSoup(html, "html.parser").select(".list-item.job-box"):
            titre = texte(bloc.select_one("h5"))
            lien = bloc.select_one("a[href]")
            if not titre or not lien:
                continue
            paragraphes = [texte(p) for p in bloc.select("p")]
            contenu = " ".join(paragraphes)
            delai = re.search(r"Submission Deadline:", contenu)
            ref = paragraphes[1].replace("REFERENCE NUMBER:", "").strip() if len(paragraphes) > 1 else ""
            avis.append(item(self.source_key, "sz-" + (ref or lien["href"].rsplit("/", 1)[-1])[:150], titre,
                             paragraphes[0] if paragraphes else "", "Eswatini", "",
                             date_libre(contenu[delai.end():delai.end() + 60]) if delai else "",
                             contenu[:1500], urljoin(self.url, lien["href"])))
        return avis


class CongoScraper(PagesScraper):
    """Congo, ARMP : tableau des derniers appels publies, sur la page d'accueil."""
    source_key = "congo"
    nom = "Congo (ARMP)"
    site = url = CONGO_URL

    def extraire(self, html):
        avis = []
        for ligne in BeautifulSoup(html, "html.parser").select("tr.marche-row-accueil"):
            ref = texte(ligne.select_one("strong"))
            titre = texte(ligne.select_one(".marche-title-accueil"))
            if not ref or not titre:
                continue
            entite = texte(ligne.select_one(".text-muted")).rstrip(".")
            avis.append(item(self.source_key, f"cg-{ref}", titre, entite, "Congo", "",
                             date_texte(texte(ligne.select_one(".date-text")), "%d/%m/%Y"),
                             f"{ref}. {entite}. {titre}", urljoin(self.url, "services-portal.php")))
        return avis


class HaitiScraper(PagesScraper):
    """Haiti, CNMP : avis publies (date de mise en ligne seulement)."""
    source_key = "haiti"
    nom = "Haiti (CNMP)"
    site = url = HAITI_URL
    sans_date_max_jours = ONG_SANS_DATE_MAX_JOURS

    def extraire(self, html):
        avis = []
        for carte in BeautifulSoup(html, "html.parser").select("article.appels-grid-card"):
            image, lien = carte.select_one("img[alt]"), carte.select_one("a[href$='.pdf']")
            # Le titre affiche est tronque ; le texte alternatif de l'image le donne en entier.
            titre = (image["alt"] if image else "") or texte(carte.select_one(".appels-card-title"))
            if not titre or not lien:
                continue
            autorite = texte(carte.select_one(".appels-authority"))
            avis.append(item(self.source_key, "ht-" + lien["href"].rsplit("/", 1)[-1][:150], titre, autorite,
                             "Haïti", date_texte(texte(carte.select_one(".appels-date-badge")), "%d/%m/%Y"), "",
                             f"{autorite}. {texte(carte.select_one('.appels-card-text'))}", lien["href"]))
        return avis


class MozambiqueScraper(PagesScraper):
    """Mozambique, UFSA : concours ouverts (bandeau de la page d'accueil)."""
    source_key = "mozambique"
    nom = "Mozambique (UFSA)"
    site = url = MOZAMBIQUE_URL

    def extraire(self, html):
        avis = []
        for bloc in BeautifulSoup(html, "html.parser").select("label.label_roll"):
            lien = bloc.select_one("a[href*='referencia=']")
            objet = texte(bloc.select_one(".lbl_objecto"))
            if not lien or not objet:
                continue
            lignes = [l.strip() for l in bloc.get_text("\n").split("\n") if l.strip()]
            modalite = lignes[0] if lignes else ""
            entite = lignes[lignes.index(objet) + 1] if objet in lignes and lignes.index(objet) + 1 < len(lignes) else ""
            ref = lien["href"].split("referencia=", 1)[1].strip()
            avis.append(item(self.source_key, f"mz-{ref}"[:200], objet, entite, "Mozambique", "",
                             texte(bloc.select_one("u")), f"{modalite}. {entite}. {objet}",
                             urljoin(self.url, lien["href"].strip())))
        return avis
