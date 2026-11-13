"""Verifie que les offres retenues sont encore en ligne chez leur source.

    manage.py verifier_liens              les actionnables jamais verifiees
    manage.py verifier_liens --toutes     toutes les retenues
    manage.py verifier_liens --source bad une source
    manage.py verifier_liens --depuis 7   celles verifiees il y a plus de 7 j
    manage.py verifier_liens --a-blanc    n'ecrit rien, montre les verdicts
"""

from collections import Counter

from django.core.management.base import BaseCommand

from apps.offres.services.lien_checker import (CLOSE, DELAI_PAR_DEFAUT, DELAIS, INTROUVABLE,
                                               a_verifier, verifier_offres)
from apps.offres.services.taches import suivre


class Command(BaseCommand):
    help = "Controle HTTP des liens des offres retenues (404, cloture annoncee)."

    def add_arguments(self, parser):
        parser.add_argument("--toutes", action="store_true")
        parser.add_argument("--source")
        parser.add_argument("--depuis", type=int, metavar="JOURS")
        parser.add_argument("--a-blanc", action="store_true")
        parser.add_argument("--tache", type=int, help="(interne) tache suivie par l'interface")

    def handle(self, *args, **o):
        with suivre(o["tache"]) as progression:
            offres = a_verifier(o["toutes"], o["source"], o["depuis"])
            if not offres:
                progression(detail="Aucune offre à vérifier.")
                self.stdout.write("Aucune offre a verifier.")
                return
            par_source = Counter(x["source"] for x in offres)
            duree = sum(DELAIS.get(s, DELAI_PAR_DEFAUT) * n for s, n in par_source.items())
            self.stdout.write(f"{len(offres)} offre(s) a verifier : {dict(par_source)}")
            self.stdout.write(f"Duree minimale (delais de politesse) : {duree / 60:.0f} min.\n")

            verdicts = verifier_offres(offres, o["a_blanc"], progression, self.stdout.write)

        self.stdout.write(f"\nVerdicts : {dict(verdicts)}")
        if o["a_blanc"]:
            self.stdout.write("Passage a blanc : rien n'a ete ecrit.")
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{verdicts[INTROUVABLE] + verdicts[CLOSE]} offre(s) retiree(s) des actionnables."))
