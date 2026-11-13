"""Collecte automatique : le traitement complet (collecte, tri, liens) chaque jour.

    manage.py planifier                 tourne en continu ; heure reglee dans l'onglet Parametres
    manage.py planifier --heure 01:30   heure imposee, ignore le reglage de l'ecran
    manage.py planifier --une-fois      un passage maintenant puis s'arrete (cron, systemd)

L'heure est relue en base chaque minute : la changer a l'ecran prend effet sans
redemarrer le planificateur. Chaque passage est une Tache comme celles des
boutons : barre de progression, journal, historique marque "auto".
"""

import time
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.offres.models import Parametres
from apps.offres.services.taches import DejaEnCours, demarrer, prochaine_execution


class Command(BaseCommand):
    help = "Lance chaque jour le traitement complet a l'heure reglee dans l'onglet Parametres."

    def add_arguments(self, parser):
        parser.add_argument("--heure", help="HH:MM, heure locale imposee (sinon : onglet Parametres)")
        parser.add_argument("--une-fois", action="store_true",
                            help="un passage maintenant, attend sa fin, puis s'arrete")

    def handle(self, *args, **o):
        self.heure_imposee = None
        if o["heure"]:
            try:
                self.heure_imposee = datetime.strptime(o["heure"], "%H:%M").time()
            except ValueError:
                raise CommandError(f"Heure illisible : {o['heure']!r}. Attendu HH:MM, ex. 06:00.")
        if o["une_fois"]:
            self.passage()
            return

        self.cible = None
        self.stdout.write(f"Planificateur actif ({settings.TIME_ZONE}).")
        while True:
            try:
                attente = self.tour()
            except Exception as exc:
                # Base injoignable : on reessaie dans une minute plutot que de tomber.
                self.stderr.write(f"Planificateur : {exc}")
                attente = 60
            time.sleep(attente)

    def tour(self) -> float:
        """Un tour de boucle : lance le passage si l'heure est venue, relit
        l'heure reglee, signale sa presence. Rend l'attente avant le suivant."""
        maintenant = timezone.localtime()
        if self.cible and maintenant >= self.cible:
            self.cible = None
            self.passage()
            maintenant = timezone.localtime()

        parametres = Parametres.charger()
        Parametres.objects.filter(pk=parametres.pk).update(planificateur_vu_le=timezone.now())
        cible = prochaine_execution(maintenant, self.heure_imposee or parametres.heure_collecte)
        if cible != self.cible:
            self.cible = cible
            self.stdout.write(f"Prochain passage : {cible:%Y-%m-%d %H:%M}.")
        # Par tranches d'une minute au plus : un changement d'heure a l'ecran,
        # ou une mise en veille de la machine, est pris en compte rapidement.
        return max(1.0, min(60.0, (self.cible - maintenant).total_seconds()))

    def passage(self):
        try:
            tache, processus = demarrer("tout", automatique=True)
        except DejaEnCours as exc:
            self.stdout.write(f"Passage ignore : {exc.tache.libelle} deja en cours.")
            return
        self.stdout.write(f"Passage lance (tache {tache.pk}, journal {tache.chemin_journal}).")
        code = processus.wait()
        tache.refresh_from_db()
        self.stdout.write(f"Passage termine (code {code}) : {tache.detail}")
