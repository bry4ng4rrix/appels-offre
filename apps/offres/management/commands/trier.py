"""Re-qualifie les offres deja en base avec le moteur de regles.

    manage.py trier                  toute la base (quelques secondes)
    manage.py trier --source boamp   une source
    manage.py trier --id ID [ID...]  des offres precises

A lancer apres toute modification de services/classifier.py.
"""

from django.core.management.base import BaseCommand

from apps.offres.models import Offre
from apps.offres.services.pipeline import PipelineService


class Command(BaseCommand):
    help = "Re-applique le classifieur sur les offres en base."

    def add_arguments(self, parser):
        groupe = parser.add_mutually_exclusive_group()
        groupe.add_argument("--source")
        groupe.add_argument("--id", nargs="+")

    def handle(self, *args, **o):
        lot = Offre.objects.all()
        if o["source"]:
            lot = lot.filter(source=o["source"])
        if o["id"]:
            lot = lot.filter(pk__in=o["id"])
        r = PipelineService.requalifier(lot)
        self.stdout.write(self.style.SUCCESS(
            f"{r['total']} offre(s) requalifiee(s), {r['retenues']} retenue(s), "
            f"{r['changees']} verdict(s) modifie(s)."))
