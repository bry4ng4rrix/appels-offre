"""Repli sémantique local pour les offres que les règles ne savent pas classer.

Ollama ne remplace pas le classifieur déterministe : il est appelé uniquement
quand celui-ci renvoie « autre ». Toute erreur ou sortie non conforme revient
aux règles, sans interrompre la collecte.
"""

import json
import re
from functools import lru_cache
from threading import Lock

import requests
from django.conf import settings
from django.utils.text import slugify

from .classifier import RuleBasedClassifier, Verdict


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


@lru_cache(maxsize=1)
def _secteurs_en_base() -> frozenset[str]:
    from apps.offres.models import Offre

    return frozenset(
        Offre.objects.exclude(secteur__isnull=True).exclude(secteur="")
        .values_list("secteur", flat=True).distinct()
    )


_SECTEURS_APPRIS = set()
_VERROU_SECTEURS = Lock()


def _secteurs_enregistres() -> frozenset[str]:
    """Secteurs existants et deja proposes dans ce processus."""
    with _VERROU_SECTEURS:
        appris = frozenset(_SECTEURS_APPRIS)
    return _secteurs_en_base() | appris


def _code_secteur(valeur: str) -> str:
    """Convertit une proposition de secteur en code stable compatible BDD."""
    code = slugify((valeur or "").strip(), allow_unicode=False).replace("-", "_")
    code = re.sub(r"_+", "_", code).strip("_")[:100].rstrip("_")
    if not code or code == "autre" or not re.fullmatch(r"[a-z0-9_]+", code):
        raise ValueError("Secteur Ollama invalide")
    return code


def _predire_secteur(item: dict) -> dict:
    titre = (item.get("titre") or "")[:500]
    description = (item.get("description") or "")[:3000]
    secteurs_existants = set(RuleBasedClassifier.SECTEURS) | set(_secteurs_enregistres())
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
    if settings.CLASSIFICATEUR_IA not in {"ollama", "gemma", "on", "true", "1"}:
        return original
    if original.secteur != "autre":
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

    # Les secteurs proposes sont enregistres directement dans Offre.secteur
    # (champ libre), puis deviennent disponibles dans les filtres et compteurs.
    # Le pipeline cree les offres en lot : memoriser aussi le secteur permet
    # a Gemma de le reutiliser avant le bulk_create de fin de source.
    with _VERROU_SECTEURS:
        _SECTEURS_APPRIS.add(secteur)

    titre = item.get("titre") or ""
    pays = RuleBasedClassifier.normaliser_texte(item.get("pays")).strip()
    nature = RuleBasedClassifier.detecter_nature(titre, item.get("source") or "")
    libelle = secteur.replace("_", " ").capitalize()
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
