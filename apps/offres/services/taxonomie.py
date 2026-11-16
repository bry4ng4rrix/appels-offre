"""Normalisation des noms de secteur pour eviter les doublons linguistiques."""

from django.utils.text import slugify


EQUIVALENCES_SECTEURS = {
    "electrical": "energie",
    "electricite": "energie",
    "electricity": "energie",
    "energy": "energie",
    "ecologie": "environnement",
    "ecology": "environnement",
}


def code_secteur(valeur: str) -> str:
    """Produit un code stable et rabat les synonymes sur le secteur canonique."""
    code = slugify((valeur or "").strip(), allow_unicode=False).replace("-", "_")
    return EQUIVALENCES_SECTEURS.get(code, code)
