"""Commande principale : collecte -> qualification -> base -> email.

    manage.py veille                     mode incremental
    manage.py veille --complet           rattrape tout le catalogue des sources
    manage.py veille --source bad        une seule source
    manage.py veille --sans-notification pas d'email
"""

from django.core.management.base import BaseCommand, CommandError

from apps.offres.services.pipeline import PipelineService


class Command(BaseCommand):
    help = "Collecte toutes les sources, qualifie et enregistre les nouvelles offres."

    def add_arguments(self, parser):
        parser.add_argument("--complet", action="store_true",
                            help="sans plafond ni arret anticipe (long)")
        parser.add_argument("--source", help="cle de source : bad, armp, boamp...")
        parser.add_argument("--sans-notification", action="store_true")

    def handle(self, *args, **o):
        try:
            retenues = PipelineService.executer(complet=o["complet"], source_filtre=o["source"],
                                                notifier=not o["sans_notification"])
        except ValueError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"Termine : {len(retenues)} offre(s) retenue(s)."))
