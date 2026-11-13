"""Toutes les actions dans l'ordre : collecte, tri de la base, verification des liens.

    manage.py tout
    manage.py tout --sans-notification
"""

from django.core.management.base import BaseCommand

from apps.offres.models import Offre
from apps.offres.services.lien_checker import CLOSE, INTROUVABLE, a_verifier, verifier_offres
from apps.offres.services.pipeline import PipelineService
from apps.offres.services.taches import suivre


class Command(BaseCommand):
    help = "Collecte + tri de toute la base + verification des liens des actionnables."

    def add_arguments(self, parser):
        parser.add_argument("--sans-notification", action="store_true")
        parser.add_argument("--tache", type=int, help="(interne) tache suivie par l'interface")

    def handle(self, *args, **o):
        with suivre(o["tache"]) as progression:
            progression.phase(1)
            retenues = PipelineService.executer(notifier=not o["sans_notification"],
                                                progression=progression)

            # Le tri de toute la base applique les regles courantes aux offres anciennes.
            progression.phase(2)
            tri = PipelineService.requalifier(Offre.objects.all(), progression)

            progression.phase(3)
            offres = a_verifier()
            verdicts = verifier_offres(offres, progression=progression, ecrire=self.stdout.write)

            resume = (f"{len(retenues)} nouvelle(s) offre(s) retenue(s) · "
                      f"{tri['changees']} verdict(s) modifié(s) · "
                      f"{len(offres)} lien(s) vérifié(s), "
                      f"{verdicts[INTROUVABLE] + verdicts[CLOSE]} retiré(s).")
            progression(detail=resume)
        self.stdout.write(self.style.SUCCESS(resume))
