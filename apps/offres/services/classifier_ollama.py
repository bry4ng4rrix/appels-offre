"""Repli sémantique local pour les offres que les règles ne savent pas classer.

Ollama ne remplace pas le classifieur déterministe : il est appelé uniquement
quand celui-ci renvoie « autre ». Toute erreur ou sortie non conforme revient
aux règles, sans interrompre la collecte.
"""

import json

import requests
from django.conf import settings

from .classifier import RuleBasedClassifier, Verdict


SCHEMA = {
    "type": "object",
    "properties": {
        "secteur": {"type": "string", "enum": ["autre", *RuleBasedClassifier.SECTEURS]},
        "confiance": {"type": "number", "minimum": 0, "maximum": 1},
        "justification": {"type": "string"},
    },
    "required": ["secteur", "confiance", "justification"],
    "additionalProperties": False,
}


def _predire_secteur(item: dict) -> dict:
    titre = (item.get("titre") or "")[:500]
    description = (item.get("description") or "")[:3000]
    secteurs = ", ".join(RuleBasedClassifier.SECTEURS)
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
                    "Retourne 'autre' si le lien avec les secteurs est insuffisant. "
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
    if resultat["secteur"] not in {"autre", *RuleBasedClassifier.SECTEURS}:
        raise ValueError("Secteur Ollama inconnu")
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

    titre = item.get("titre") or ""
    pays = RuleBasedClassifier.normaliser_texte(item.get("pays")).strip()
    nature = RuleBasedClassifier.detecter_nature(titre, item.get("source") or "")
    categorie = f"{secteur.capitalize()} - {nature.capitalize()}"

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
