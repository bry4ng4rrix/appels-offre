"""Toutes les actions dans l'ordre : collecte, tri de la base, verification des liens.

    manage.py tout
    manage.py tout --sans-notification
"""

from django.core.management.base import BaseCommand

from apps.offres.models import Offre
from apps.offres.services.lien_checker import CLOSE, INTROUVABLE, a_verifier, verifier_offres
from apps.offres.services import alertes
from apps.offres.services.pipeline import PipelineService
from apps.offres.services.taches import suivre


class Command(BaseCommand):
    help = "Collecte + tri des offres pas encore triees + verification des liens des actionnables."

    def add_arguments(self, parser):
        parser.add_argument("--sans-notification", action="store_true")
        parser.add_argument("--tache", type=int, help="(interne) tache suivie par l'interface")

    def handle(self, *args, **o):
        with suivre(o["tache"]) as progression:
            # Apres une coupure, la tache reprend a la phase ou elle s'etait arretee.
            deja = progression.phase_atteinte
            if deja > 1:
                self.stdout.write(f"Reprise a la phase {deja} : les precedentes sont faites.")
            if deja <= 1:
                progression.phase(1)
                retenues = PipelineService.executer(notifier=not o["sans_notification"],
                                                    progression=progression)
            else:
                retenues = Offre.objects.filter(pertinent=True, date_ajout__gte=progression.debut)

            # Tri des seules offres sans marque « triee le » : la collecte marque deja
            # les siennes. Retrier toute la base reste le role de la tache « Tri ».
            if deja <= 2:
                progression.phase(2)
                tri = PipelineService.requalifier(Offre.objects.filter(trie_le__isnull=True),
                                                  progression)
                progression.sauver(tri=tri["changees"], triees=tri["total"])

            # La verification ne reprend que les liens jamais verifies : elle
            # reprend donc d'elle-meme la ou elle s'etait arretee.
            progression.phase(3)
            offres = a_verifier()
            verdicts = verifier_offres(offres, progression=progression, ecrire=self.stdout.write)

            triees = progression.etat.get("triees", 0)
            resume = (f"{len(retenues)} nouvelle(s) offre(s) retenue(s) · "
                      f"{f'{triees} offre(s) non triée(s) traitée(s), ' if triees else 'rien à retrier, '}"
                      f"{progression.etat.get('tri', 0)} verdict(s) modifié(s) · "
                      f"{len(offres)} lien(s) vérifié(s), "
                      f"{verdicts[INTROUVABLE] + verdicts[CLOSE]} retiré(s).")
            progression(detail=resume)
        self.stdout.write(self.style.SUCCESS(resume))

        if not o["sans_notification"]:
            # Apres les liens : une offre retiree entre-temps ne part pas par email.
            try:
                bilan = alertes.traiter()
                self.stdout.write(f"Alertes : {bilan['creees']} nouvelle(s), "
                                  f"{bilan['emails']} email(s) envoye(s), {bilan['echecs']} echec(s).")
            except Exception as exc:
                # Les offres sont deja en base : des alertes en panne ne font pas echouer le passage.
                self.stderr.write(f"Alertes en echec : {exc}")
