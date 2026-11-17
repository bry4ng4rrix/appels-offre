"""Normalisation des secteurs et des pays pour eviter les doublons."""

from django.utils.text import slugify

from .geo import normaliser as normaliser_lieu


EQUIVALENCES_SECTEURS = {
    "electrical": "energie",
    "electricite": "energie",
    "electricity": "energie",
    "energy": "energie",
    "ecologie": "environnement",
    "ecology": "environnement",
    # Gemma dit souvent « pas de secteur » autrement : ce n'est pas un nouveau secteur.
    "autres": "autre", "other": "autre", "others": "autre", "divers": "autre",
    "aucun": "autre", "none": "autre", "inconnu": "autre", "general": "autre",
    "non_classe": "autre", "non_classifie": "autre",
}


def code_secteur(valeur: str) -> str:
    """Produit un code stable et rabat les synonymes sur le secteur canonique."""
    code = slugify((valeur or "").strip(), allow_unicode=False).replace("-", "_")
    return EQUIVALENCES_SECTEURS.get(code, code)


def code_pays(valeur: str) -> str:
    """Produit une clé stable pour rapprocher accents et ponctuation des lieux."""
    return slugify(normaliser_lieu(valeur), allow_unicode=False)[:100]
