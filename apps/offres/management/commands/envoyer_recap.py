"""Envoie par email le recapitulatif des offres actionnables recentes.

    manage.py envoyer_recap             ajoutees depuis 1 jour
    manage.py envoyer_recap --jours 7
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.offres.models import Offre, actionnables
from apps.offres.services.notification import NotificationService


class Command(BaseCommand):
    help = "Envoie le recapitulatif des offres retenues recentes."

    def add_arguments(self, parser):
        parser.add_argument("--jours", type=int, default=1)

    def handle(self, *args, **o):
        depuis = timezone.now() - timedelta(days=o["jours"])
        offres = list(actionnables(Offre.objects.filter(date_ajout__gte=depuis))
                      .order_by("date_limite"))
        NotificationService.envoyer_email(offres)
