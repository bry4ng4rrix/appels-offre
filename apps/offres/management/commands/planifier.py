"""Collecte automatique : le traitement complet (collecte, tri, liens) chaque jour.

    manage.py planifier                 tourne en continu, passage quotidien a VEILLE_HEURE
    manage.py planifier --heure 01:30   autre heure (locale, TIME_ZONE)
    manage.py planifier --une-fois      un passage maintenant puis s'arrete (cron, systemd)

Chaque passage est une Tache comme celles des boutons : il apparait dans la
barre de progression et dans l'historique de la page Taches, marque "auto".
"""

import time
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.offres.services.taches import DejaEnCours, demarrer


def prochaine_execution(maintenant: datetime, heure) -> datetime:
    """Prochaine occurrence de `heure` apres `maintenant` (datetime locale)."""
    cible = maintenant.replace(hour=heure.hour, minute=heure.minute, second=0, microsecond=0)
    return cible if cible > maintenant else cible + timedelta(days=1)


class Command(BaseCommand):
    help = "Lance chaque jour le traitement complet a heure fixe."

    def add_arguments(self, parser):
        parser.add_argument("--heure", default=settings.VEILLE_HEURE,
                            help="HH:MM, heure locale (defaut : VEILLE_HEURE)")
        parser.add_argument("--une-fois", action="store_true",
                            help="un passage maintenant, attend sa fin, puis s'arrete")

    def handle(self, *args, **o):
        try:
            heure = datetime.strptime(o["heure"], "%H:%M").time()
        except ValueError:
            raise CommandError(f"Heure illisible : {o['heure']!r}. Attendu HH:MM, ex. 06:00.")
        if o["une_fois"]:
            self.passage()
            return

        self.stdout.write(f"Planificateur actif : traitement complet chaque jour a "
                          f"{heure:%H:%M} ({settings.TIME_ZONE}).")
        while True:
            cible = prochaine_execution(timezone.localtime(), heure)
            self.stdout.write(f"Prochain passage : {cible:%Y-%m-%d %H:%M}.")
            # Par tranches d'une minute : une mise en veille de la machine ne
            # decale pas le passage d'une journee.
            while (reste := (cible - timezone.localtime()).total_seconds()) > 0:
                time.sleep(min(60, reste))
            try:
                self.passage()
            except Exception as exc:
                # Base injoignable a l'heure dite : on reessaiera demain plutot
                # que de faire tomber le planificateur.
                self.stderr.write(f"Passage impossible : {exc}")

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
