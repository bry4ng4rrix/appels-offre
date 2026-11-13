"""Qualification des offres par regles deterministes (remplace le LLM Ollama).

Nature (marche / emploi), secteur, pertinence geographique : < 1 ms par offre.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional


@dataclass
class Verdict:
    pertinent: bool
    nature: str
    secteur: str
    categorie: str
    raison: str


def _motifs(*mots: str) -> re.Pattern:
    # \b en tete ET en fin (pluriel tolere) : sans cela "erp" matchait
    # "interpretation", "wash" "Washington" et "esia" "Indonesia".
    return re.compile(r"\b(?:" + "|".join(mots) + r")s?\b")


class RuleBasedClassifier:
    EMPLOI_KEYWORDS = _motifs(
        r"comptable", r"chauffeur", r"ingenieur", r"assistant", r"assistante",
        r"coordonnateur", r"coordinateur", r"chercheur", r"developpeur",
        r"analyste", r"charge de", r"chargee de", r"responsable",
        r"consultant individuel", r"individual consultant", r"vacancy",
        r"job announcement", r"recrutement d['’]un",
        # UNjobnet et les agences publient en anglais
        r"officer", r"specialist", r"manager", r"associate", r"intern(?:ship)?",
        r"engineer", r"advis[eo]r",
    )
    #: Testes AVANT les metiers : "Recrutement d'un cabinet charge de l'audit"
    #: est un marche, meme s'il contient "charge de".
    MARCHE_KEYWORDS = _motifs(
        r"firme", r"cabinet", r"bureau d['’]etudes?", r"fourniture", r"travaux",
        r"prestation", r"acquisition", r"selection d['’]une societe",
        r"selection d['’]une firme", r"consulting firm", r"supply of", r"works",
    )
    #: Sources qui ne publient que des postes.
    SOURCES_EMPLOI = {"unjobnet"}

    #: Contrats passes avec une PERSONNE PHYSIQUE (PNUD "IC", BAD "consultant
    #: individuel"). Repris tel quel de l'ancien filet de coherence : verifie
    #: sur 5 735 offres, 35 bascules relues une a une, aucun faux positif.
    #: Applique au titre BRUT (casse comprise, "IC" en majuscules).
    MARQUEURS_CONTRAT_INDIVIDUEL = re.compile(
        r"(\b[A-Z]{2,6}-[A-Z]{0,4}IC-\d"
        r"|^\s*IC\b"
        r"|\bIC\s+\d{1,3}/\d{4}\b"
        r"|individual\s+contract(or)?\b"
        r"|consultant\s+individuel"
        r"|consultant\s+national\b|national\s+consultant\b"
        r"|consultor[ií]a\b)", re.I)

    SECTEURS = {
        "informatique": _motifs(
            r"logiciel", r"software", r"developpement web", r"web development",
            r"systeme d['’]information", r"information system", r"erp", r"crm",
            r"base de donnees", r"database", r"numerisation", r"digitalis\w*",
            r"digitaliz\w*", r"transformation numerique", r"materiel informatique",
            r"it equipment", r"serveur", r"reseau informatique", r"call cent(?:er|re)",
            r"centre d['’]appels?", r"bpo", r"support client", r"marketing digital",
            r"seo", r"site ?web", r"website", r"application mobile", r"cloud",
            r"cybersecurite", r"cybersecurity", r"informatique", r"ict",
        ),
        "eau": _motifs(
            r"adduction d['’]eau", r"water supply", r"forage", r"drilling", r"borehole",
            r"chateau d['’]eau", r"potabilisation", r"station de pompage",
            r"pumping station", r"assainissement", r"sanitation", r"sewerage",
            r"eaux usees", r"wastewater", r"drainage", r"wash", r"hydraulique",
            r"water treatment",
        ),
        "environnement": _motifs(
            r"gestion des dechets", r"waste management", r"biodiversite",
            r"biodiversity", r"aire protegee", r"conservation", r"reforestation",
            r"changement climatique", r"climate change", r"resilience", r"carbone",
            r"etude d['’]impact environnemental", r"eies", r"esia",
            r"energie renouvelable", r"renewable energy", r"solaire", r"solar",
            r"eolien", r"depollution",
        ),
        "agriculture": _motifs(
            r"production agricole", r"semence", r"seed", r"intrant",
            r"elevage", r"livestock", r"peche", r"fisheries", r"aquaculture",
            r"irrigation", r"hydro-agricole", r"genie rural", r"chaine de valeur",
            r"value chain", r"securite alimentaire", r"food security", r"sylviculture",
        ),
        "construction": _motifs(
            r"batiment", r"building", r"genie civil", r"civil works",
            r"travaux publics", r"voirie", r"route", r"road", r"pont", r"bridge",
            r"rehabilitation", r"extension", r"terrassement", r"second oeuvre",
            r"electricite", r"plomberie", r"materiaux de construction", r"construction",
        ),
    }

    #: L'ordre tranche les offres multi-secteurs (regles de l'ancien prompt) :
    #: un logiciel pour l'irrigation reste "informatique", un chateau d'eau
    #: reste "eau" meme si c'est un ouvrage bati.
    PRIORITES_SECTEUR = ["informatique", "eau", "environnement", "agriculture", "construction"]
    PAYS_OCEAN_INDIEN = ("madagascar", "reunion", "mayotte", "maurice", "mauritius",
                         "comores", "comoros", "seychelles")

    @staticmethod
    def normaliser_texte(texte: str) -> str:
        t = unicodedata.normalize("NFKD", (texte or "").lower().replace("œ", "oe"))
        return "".join(c for c in t if not unicodedata.combining(c))

    @classmethod
    def detecter_nature(cls, titre: str, source: str = "") -> str:
        if source in cls.SOURCES_EMPLOI or cls.MARQUEURS_CONTRAT_INDIVIDUEL.search(titre or ""):
            return "emploi"
        texte = cls.normaliser_texte(titre)
        if cls.MARCHE_KEYWORDS.search(texte):
            return "marche"
        if cls.EMPLOI_KEYWORDS.search(texte):
            return "emploi"
        return "marche"

    @classmethod
    def detecter_secteur(cls, texte: str) -> tuple[str, Optional[str]]:
        for secteur in cls.PRIORITES_SECTEUR:
            m = cls.SECTEURS[secteur].search(texte)
            if m:
                return secteur, m.group(0)
        return "autre", None

    @classmethod
    def evaluer(cls, item: dict) -> Verdict:
        titre = item.get("titre") or ""
        desc = item.get("description") or ""
        pays = cls.normaliser_texte(item.get("pays")).strip()
        texte = cls.normaliser_texte(f"{titre} {desc}")

        nature = cls.detecter_nature(titre, item.get("source") or "")
        secteur, mot = cls.detecter_secteur(texte)
        categorie = f"{secteur.capitalize()} - {nature.capitalize()}"

        if secteur == "autre":
            return Verdict(False, nature, "autre", "Hors périmètre", "Aucun mot-clé ciblé")

        # Une societe ne peut pas signer un contrat passe avec une personne.
        if cls.MARQUEURS_CONTRAT_INDIVIDUEL.search(titre):
            return Verdict(False, "emploi", secteur, categorie, "Contrat individuel")

        est_mg = "madagascar" in pays or pays == "mg"
        if est_mg:
            pertinent, raison = True, f"Cible Madagascar ({mot})"
        elif secteur == "informatique":
            pertinent, raison = True, f"IT télétravaillable ({mot})"
        elif any(p in pays for p in cls.PAYS_OCEAN_INDIEN):
            pertinent, raison = True, f"Zone Océan Indien ({mot})"
        else:
            pertinent, raison = False, f"Hors zone géographique pour {secteur}"

        return Verdict(pertinent, nature, secteur, categorie, raison[:60])
