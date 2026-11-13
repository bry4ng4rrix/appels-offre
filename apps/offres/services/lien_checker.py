"""Verifie qu'une offre est encore en ligne chez sa source.

L'echeance manque pour l'essentiel des offres (BAD, Banque mondiale,
UNjobnet) et ne figure pas sur leurs pages. On repond donc a une autre
question : l'offre est-elle encore en ligne ? Un 404, ou une phrase qui
annonce la cloture.

PRINCIPE : on ne marque close que sur un signal EXPLICITE. Une opportunite
masquee a tort disparait sans que personne ne s'en apercoive ; une offre
close qui traine se voit tout de suite.
"""

import re

import requests
from bs4 import BeautifulSoup

from Offre.sources import (BAD_PAGE_DELAY, COI_PAGE_DELAY, FID_PAGE_DELAY,
                           MNP_PAGE_DELAY, UNJOBNET_PAGE_DELAY, WWF_PAGE_DELAY)

#: Delai a respecter entre deux requetes, PAR SOURCE. Ce ne sont pas des
#: reglages de confort : la BAD, le WWF et MNP imposent "Crawl-delay: 10"
#: dans leur robots.txt.
DELAIS = {
    "bad": BAD_PAGE_DELAY,
    "wwf": WWF_PAGE_DELAY,
    "mnp": MNP_PAGE_DELAY,
    "coi": COI_PAGE_DELAY,
    "fid": FID_PAGE_DELAY,
    "unjobnet": UNJOBNET_PAGE_DELAY,
}
DELAI_PAR_DEFAUT = 1.0

ENTETES = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr,en;q=0.8",
}

#: Phrases qui annoncent SANS AMBIGUITE que c'est termine. Relevees sur les
#: sources reelles -- UNjobnet dit mot pour mot "This position is no longer
#: open". Volontairement courte : chaque motif ajoute ici peut faire
#: disparaitre une offre, il doit donc etre indiscutable.
CLOTURE = re.compile(
    r"no longer (open|available|accepting)"
    r"|this (position|vacancy|job) (is|has been) closed"
    r"|applications? (are )?(now )?closed"
    r"|cette (offre|annonce) n[e'’ ]est plus (disponible|en ligne)"
    r"|avis (cloture|clôturé|annule|annulé)"
    r"|appel d[e'’ ]offres? (cloture|clôturé|annule|annulé)"
    r"|candidatures? (cloture|clôturée|closes)"
    r"|offre (est |a ete |a été )?(expiree|expirée|pourvue|attribuee|attribuée)",
    re.I)

#: Ce qui ressemble a une cloture sans en etre une. Ces tournures figurent
#: dans les MENTIONS LEGALES ou les avertissements de plusieurs sites --
#: UNjobnet met en garde contre les annonces perimees sur CHACUNE de ses
#: pages, y compris les ouvertes.
FAUX_AMIS = re.compile(
    r"confirm the role and closing date"
    r"|before applying"
    r"|beware|scam|fraud"
    r"|si l[e'’ ]offre (est|etait) close",
    re.I)

#: Marqueur de gabarit non rendu ("{{waiting}}", "{{offer.title}}"...).
#:
#: UNjobnet est une application JavaScript : son HTML statique porte LES DEUX
#: branches de chaque condition. La phrase "This position is no longer open"
#: y figure donc sur toutes les pages, ouvertes comprises -- verifie sur une
#: offre dont l'echeance annoncee etait le 30 septembre.
#:
#: Une phrase voisine d'un tel marqueur n'est pas du contenu : c'est du
#: gabarit. Elle ne prouve rien.
GABARIT = re.compile(r"\{\{[^}]{0,60}\}\}")

#: Distance en deca de laquelle un marqueur de gabarit disqualifie une phrase.
#: Constate : "{{waiting}} This position is no longer open" -- douze
#: caracteres. La marge couvre les gabarits plus longs.
PORTEE_GABARIT = 150

OUVERTE, INTROUVABLE, CLOSE, ILLISIBLE = "ouverte", "introuvable", "close", "illisible"


def classer(reponse, texte: str) -> tuple:
    """Rend (etat, justification) pour une page recuperee.

    `texte` est le contenu textuel de la page, deja aplati.
    """
    if reponse.status_code in (404, 410):
        return INTROUVABLE, f"HTTP {reponse.status_code}"
    if reponse.status_code >= 400:
        # 403, 500... : le site nous refuse ou tombe. Ce n'est PAS un signal
        # de cloture, et le traiter comme tel masquerait des offres valides
        # au premier hoquet du serveur.
        return ILLISIBLE, f"HTTP {reponse.status_code}"

    # Le motif de cloture est cherche APRES avoir retire les passages qui le
    # contiennent pour de mauvaises raisons.
    propre = FAUX_AMIS.sub(" ", texte)
    for trouve in CLOTURE.finditer(propre):
        amont = propre[max(0, trouve.start() - PORTEE_GABARIT):trouve.start()]
        if GABARIT.search(amont):
            # Gabarit non rendu : la phrase est dans le modele, pas dans le
            # contenu. Continuer -- une autre occurrence peut etre reelle.
            continue
        debut = max(0, trouve.start() - 60)
        return CLOSE, propre[debut:trouve.end() + 60].strip()
    return OUVERTE, ""


#: Balises retirees avant lecture : elles portent de l'interface, pas le
#: contenu de l'annonce.
#:
#: Corrige un second faux positif, de nature differente du gabarit : les
#: pages UNjobnet portent un formulaire de signalement dont le menu deroulant
#: propose "No longer available" -- ce qui declenchait la detection sur
#: TOUTES les offres de la source. Rapiecer motif par motif serait sans fin ;
#: retirer les elements d'interface est structurel et vaut pour toute source.
BALISES_INTERFACE = ("script", "style", "nav", "footer", "header", "form",
                     "select", "option", "button", "aside", "noscript")


def texte_utile(html: str) -> str:
    """Le texte de la page, prive de ses elements d'interface."""
    soup = BeautifulSoup(html, "html.parser")
    for balise in soup.select(",".join(BALISES_INTERFACE)):
        balise.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))


def verifier(offre: dict) -> tuple:
    """Ouvre le lien d'une offre et rend (etat, justification)."""
    lien = (offre.get("lien") or "").strip()
    if not lien:
        return ILLISIBLE, "aucun lien"
    try:
        reponse = requests.get(lien, headers=ENTETES, timeout=45,
                               allow_redirects=True)
    except requests.RequestException as exc:
        return ILLISIBLE, f"{type(exc).__name__}: {str(exc)[:60]}"

    texte = ""
    if reponse.status_code < 400:
        try:
            texte = texte_utile(reponse.text)
        except Exception as exc:            # page illisible, pas close
            return ILLISIBLE, f"analyse impossible : {str(exc)[:50]}"
    return classer(reponse, texte)
