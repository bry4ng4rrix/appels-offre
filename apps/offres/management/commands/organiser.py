"""Organisation de nuit : ranger les catalogues, puis mieux classer les nouvelles offres.

    manage.py organiser

Lancée chaque nuit par le planificateur (heure réglée dans Paramètres) ;
voir services/organisation.py pour le détail des deux phases.
"""

from django.core.management.base import BaseCommand

from apps.offres.services import organisation
from apps.offres.services.taches import suivre


class Command(BaseCommand):
    help = "Organisation de nuit : catalogues (secteurs, catégories, pays) puis classement des nouvelles offres."

    def add_arguments(self, parser):
        parser.add_argument("--tache", type=int, help="(interne) tache suivie par l'interface")

    def handle(self, *args, **o):
        with suivre(o["tache"]) as progression:
            # Apres une coupure, la tache reprend a la phase ou elle s'etait arretee.
            if progression.phase_atteinte <= 1:
                progression.phase(1)
                progression.sauver(**organisation.catalogues(progression))
            progression.phase(2)
            r = organisation.classer(progression)
            e = progression.etat
            resume = (f"Catalogues : {e.get('fusionnes', 0)} offre(s) au secteur unifié, "
                      f"{e.get('secteurs_ajoutes', 0)} secteur(s) ajouté(s), "
                      f"{e.get('categories', 0)} catégorie(s) mise(s) à jour · "
                      f"Classement : {r['total']} offre(s) reclassée(s), "
                      f"{r['changees']} verdict(s) modifié(s).")
            progression(detail=resume)
        self.stdout.write(self.style.SUCCESS(resume))
