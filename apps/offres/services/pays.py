"""Synchronisation des lieux rencontrés avec le catalogue de filtres."""

from apps.offres.models import Pays
from apps.offres.services.taxonomie import code_pays


def synchroniser_pays(valeurs):
    """Ajoute les nouveaux libellés sans réactiver les entrées désactivées."""
    a_creer = {}
    for valeur in valeurs:
        nom = (valeur or "").strip()[:100]
        code = code_pays(nom)
        if nom and code:
            a_creer.setdefault(code, nom)
    existants = set(Pays.objects.filter(code__in=a_creer).values_list("code", flat=True))
    Pays.objects.bulk_create([
        Pays(code=code, nom=nom) for code, nom in a_creer.items()
        if code not in existants
    ], ignore_conflicts=True)
