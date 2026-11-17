"""Alertes email des nouvelles offres, hors du traitement complet.

    manage.py envoyer_alertes

Le traitement complet (`tout`, toutes les 6 h) les envoie déjà à la fin de
chaque passage ; cette commande sert à relancer à la main (échecs, essais).
"""

from django.core.management.base import BaseCommand

from apps.offres.services import alertes


class Command(BaseCommand):
    help = "Prépare et envoie les alertes email des nouvelles offres."

    def handle(self, *args, **o):
        bilan = alertes.traiter()
        self.stdout.write(f"{bilan['creees']} notification(s) créée(s), {bilan['emails']} email(s) "
                          f"envoyé(s) ({bilan['offres']} offre(s)), {bilan['echecs']} échec(s).")
