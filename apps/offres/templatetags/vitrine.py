"""Panneau des pages de connexion et d'inscription : une illustration et le
nombre d'offres ouvertes, sans les sources qui interdisent la rediffusion.
"""

from django import template
from django.conf import settings

from apps.offres.services.correspondance import ouvertes

register = template.Library()


@register.inclusion_tag("offres/_tableau_echeances.html")
def tableau_echeances():
    lot = ouvertes()
    if settings.API_PUBLIQUE_SOURCES_EXCLUES:
        lot = lot.exclude(source__in=settings.API_PUBLIQUE_SOURCES_EXCLUES)
    return {"total": lot.count()}


@register.inclusion_tag("offres/_credits_explications.html", takes_context=True)
def credits_explications(context):
    """Crédits et plans, sous la FAQ de l'accueil et sous « Lire la carte »."""
    from apps.offres.models import Inscription, Plan
    return {"user": context.get("user"), "essai_jours": Inscription.ESSAI_JOURS,
            "plans": Plan.objects.filter(actif=True)}
