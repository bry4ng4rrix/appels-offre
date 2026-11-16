"""Repli sémantique local pour les offres que les règles ne savent pas classer.

Ollama ne remplace pas le classifieur déterministe : il est appelé uniquement
quand celui-ci renvoie « autre ». Toute erreur ou sortie non conforme revient
aux règles, sans interrompre la collecte.
"""

import json
import re
from threading import Lock
from time import monotonic

import requests
from django.conf import settings
from django.db import OperationalError, ProgrammingError

from .classifier import RuleBasedClassifier, Verdict
from .taxonomie import code_secteur


SCHEMA = {
    "type": "object",
    "properties": {
        # Le secteur est volontairement libre : Gemma peut proposer un code
        # absent des règles. Il est normalise et borne avant d'etre stocke.
        "secteur": {"type": "string"},
        "confiance": {"type": "number", "minimum": 0, "maximum": 1},
        "justification": {"type": "string"},
    },
    "required": ["secteur", "confiance", "justification"],
    "additionalProperties": False,
}


_SECTEURS_APPRIS = set()
_VERROU_SECTEURS = Lock()
_CATALOGUE_CACHE = {}
_CATALOGUE_CACHE_MAJ = 0.0


def _fiche_catalogue(code: str):
    """Cache bref : les traitements ne font pas une requête SQL par offre."""
    global _CATALOGUE_CACHE, _CATALOGUE_CACHE_MAJ
    maintenant = monotonic()
    with _VERROU_SECTEURS:
        if maintenant - _CATALOGUE_CACHE_MAJ > 30:
            from apps.offres.models import Secteur
            try:
                _CATALOGUE_CACHE = {
                    secteur: (nom, actif)
                    for secteur, nom, actif in Secteur.objects.values_list("code", "nom", "actif")
                }
            except (OperationalError, ProgrammingError):
                # Au premier démarrage, le planificateur peut devancer la
                # migration lancée par le conteneur web.
                _CATALOGUE_CACHE = {}
            _CATALOGUE_CACHE_MAJ = maintenant
        return _CATALOGUE_CACHE.get(code)


def _secteur_desactive(code: str) -> bool:
    fiche = _fiche_catalogue(code)
    return fiche is not None and not fiche[1]


def _secteurs_enregistres() -> frozenset[str]:
    """Secteurs actifs du catalogue, de l'historique et du processus courant."""
    from apps.offres.models import Offre, Secteur

    with _VERROU_SECTEURS:
        appris = frozenset(_SECTEURS_APPRIS)
    try:
        actifs = set(Secteur.objects.filter(actif=True).values_list("code", flat=True))
        inactifs = set(Secteur.objects.filter(actif=False).values_list("code", flat=True))
    except (OperationalError, ProgrammingError):
        actifs, inactifs = set(), set()
    historiques = set(
        Offre.objects.exclude(secteur__isnull=True).exclude(secteur="")
        .values_list("secteur", flat=True).distinct()
    ) - inactifs
    return ((set(RuleBasedClassifier.SECTEURS) - inactifs) | actifs
            | historiques | (appris - inactifs))


def _code_secteur(valeur: str) -> str:
    """Convertit une proposition de secteur en code stable compatible BDD."""
    code = code_secteur(valeur)
    code = re.sub(r"_+", "_", code).strip("_")[:100].rstrip("_")
    if not code or code == "autre" or not re.fullmatch(r"[a-z0-9_]+", code):
        raise ValueError("Secteur Ollama invalide")
    return code


def _predire_secteur(item: dict) -> dict:
    titre = (item.get("titre") or "")[:500]
    description = (item.get("description") or "")[:3000]
    secteurs_existants = set(_secteurs_enregistres())
    secteurs = ", ".join(sorted(secteurs_existants))
    reponse = requests.post(
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        json={
            "model": settings.OLLAMA_MODEL,
            "stream": False,
            "format": SCHEMA,
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": (
                    "Tu classes des appels d'offres en français ou en anglais. "
                    "Choisis le secteur principal d'après l'objet acheté ou les travaux. "
                    "Ne déduis pas un secteur à partir du nom d'un pays ou d'une organisation. "
                    "Réutilise exactement le code d'un secteur existant si son sens correspond. "
                    "Si aucun secteur existant ne convient, propose un nouveau code court, "
                    "en français, en minuscules et avec des underscores (exemple: sante_animale). "
                    "Ne crée pas de sous-secteur qui n'est pas justifié par le texte. "
                    "Retourne 'autre' si le lien avec un secteur est insuffisant. "
                    "Donne une confiance entre 0.0 et 1.0. La justification doit être brève "
                    "et fondée sur le texte fourni. "
                    f"Secteurs autorisés : {secteurs}."
                )},
                {"role": "user", "content": f"Titre : {titre}\nDescription : {description}"},
            ],
        },
        timeout=settings.OLLAMA_TIMEOUT,
    )
    reponse.raise_for_status()
    contenu = reponse.json()["message"]["content"]
    resultat = json.loads(contenu)
    if resultat["secteur"] != "autre":
        resultat["secteur"] = _code_secteur(resultat["secteur"])
    confiance = float(resultat["confiance"])
    if not 0 <= confiance <= 1:
        raise ValueError("Confiance Ollama invalide")
    return {**resultat, "confiance": confiance}


def evaluer(item: dict) -> Verdict:
    """Utilise Gemma pour les cas inconnus ; garde le verdict de règles sinon."""
    original = RuleBasedClassifier.evaluer(item)
    if original.secteur != "autre" and not _secteur_desactive(original.secteur):
        fiche = _fiche_catalogue(original.secteur)
        if fiche:
            categorie = f"{fiche[0]} - {original.nature.capitalize()}"
            return Verdict(original.pertinent, original.nature, original.secteur,
                           categorie, original.raison)
        return original
    if original.secteur != "autre":
        # Un secteur désactivé dans les paramètres ne doit plus être attribué
        # par les règles. Son offre reste conservée avec un verdict hors périmètre.
        original = Verdict(False, original.nature, "autre", "Hors périmètre",
                           "Secteur désactivé")
    if settings.CLASSIFICATEUR_IA not in {"ollama", "gemma", "on", "true", "1"}:
        return original

    try:
        resultat = _predire_secteur(item)
    except (requests.RequestException, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Ollama ({settings.OLLAMA_MODEL}) indisponible ou réponse invalide : {exc}. Règles conservées.")
        return original

    secteur = resultat["secteur"]
    confiance = resultat["confiance"]
    if secteur == "autre" or confiance < 0.65:
        return original
    if _secteur_desactive(secteur):
        return original

    from apps.offres.models import Secteur
    try:
        fiche = Secteur.objects.filter(code=secteur).first()
    except (OperationalError, ProgrammingError):
        fiche = None
    if fiche and not fiche.actif:
        return original
    if not fiche:
        nom = secteur.replace("_", " ").capitalize()
        try:
            Secteur.objects.get_or_create(code=secteur, defaults={"nom": nom})
        except (OperationalError, ProgrammingError):
            # L'offre reste classée; le prochain re-tri inscrira le secteur.
            pass
        with _VERROU_SECTEURS:
            _CATALOGUE_CACHE.pop(secteur, None)

    # Les secteurs proposes sont enregistres directement dans Offre.secteur
    # (champ libre), puis deviennent disponibles dans les filtres et compteurs.
    # Le pipeline cree les offres en lot : memoriser aussi le secteur permet
    # a Gemma de le reutiliser avant le bulk_create de fin de source.
    with _VERROU_SECTEURS:
        _SECTEURS_APPRIS.add(secteur)

    titre = item.get("titre") or ""
    pays = RuleBasedClassifier.normaliser_texte(item.get("pays")).strip()
    nature = RuleBasedClassifier.detecter_nature(titre, item.get("source") or "")
    libelle = fiche.nom if fiche else nom
    categorie = f"{libelle} - {nature.capitalize()}"

    if RuleBasedClassifier.MARQUEURS_CONTRAT_INDIVIDUEL.search(titre):
        return Verdict(False, "emploi", secteur, categorie, "Contrat individuel")

    est_mg = "madagascar" in pays or pays == "mg"
    if est_mg:
        pertinent, zone = True, "Madagascar"
    elif secteur == "informatique":
        pertinent, zone = True, "IT télétravaillable"
    elif any(p in pays for p in RuleBasedClassifier.PAYS_OCEAN_INDIEN):
        pertinent, zone = True, "Océan Indien"
    else:
        pertinent, zone = False, f"Hors zone géographique pour {secteur}"

    justification = (resultat.get("justification") or "Secteur détecté par Gemma").strip()[:90]
    return Verdict(pertinent, nature, secteur, categorie,
                   f"Gemma {confiance:.0%} : {justification}"[:60] if pertinent else zone[:60])
