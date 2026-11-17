"""Tableau d'échéances des pages de connexion et d'inscription.

Il montre à un visiteur ce que contient l'application : quelques offres
réelles qui clôturent bientôt. Rien de plus que ce que l'API publique
expose déjà, et sans les sources qui interdisent la rediffusion.
"""

from datetime import timedelta

from django import template
from django.conf import settings
from django.utils import timezone

from apps.offres.services import geo
from apps.offres.services.correspondance import ouvertes

register = template.Library()


@register.inclusion_tag("offres/_tableau_echeances.html")
def tableau_echeances(nombre=5):
    aujourdhui = timezone.now().date()
    lot = ouvertes()
    if settings.API_PUBLIQUE_SOURCES_EXCLUES:
        lot = lot.exclude(source__in=settings.API_PUBLIQUE_SOURCES_EXCLUES)
    # Les plus recemment collectees parmi celles qui ferment dans le mois,
    # une par pays : un lot frais vient souvent d'une seule source.
    candidates = (lot.filter(date_limite__gt=aujourdhui, date_limite__lte=aujourdhui + timedelta(days=30))
                  .only("titre", "organisation", "pays", "date_limite").order_by("-date_ajout")[:500])
    offres, vus = [], set()
    for offre in candidates:
        if geo.normaliser(offre.pays) not in vus:
            vus.add(geo.normaliser(offre.pays))
            offres.append(offre)
        if len(offres) == nombre:
            break
    for offre in offres:
        offre.jours = (offre.date_limite - aujourdhui).days
    offres.sort(key=lambda o: o.date_limite)
    return {"offres": offres, "total": lot.count()}
