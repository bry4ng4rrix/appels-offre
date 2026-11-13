"""Verifie que les offres retenues sont encore en ligne chez leur source.

    manage.py verifier_liens              les actionnables jamais verifiees
    manage.py verifier_liens --toutes     toutes les retenues
    manage.py verifier_liens --source bad une source
    manage.py verifier_liens --depuis 7   celles verifiees il y a plus de 7 j
    manage.py verifier_liens --a-blanc    n'ecrit rien, montre les verdicts
"""

import time
from collections import Counter
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.offres.models import Offre, actionnables
from apps.offres.services.lien_checker import (CLOSE, DELAI_PAR_DEFAUT, DELAIS,
                                               INTROUVABLE, OUVERTE, verifier)


class Command(BaseCommand):
    help = "Controle HTTP des liens des offres retenues (404, cloture annoncee)."

    def add_arguments(self, parser):
        parser.add_argument("--toutes", action="store_true")
        parser.add_argument("--source")
        parser.add_argument("--depuis", type=int, metavar="JOURS")
        parser.add_argument("--a-blanc", action="store_true")

    def handle(self, *args, **o):
        lot = Offre.objects.filter(pertinent=True, lien__isnull=False).exclude(lien="")
        if not o["toutes"]:
            lot = actionnables(lot)
        if o["source"]:
            lot = lot.filter(source=o["source"])
        if o["depuis"] is not None:
            limite = timezone.now() - timedelta(days=o["depuis"])
            lot = lot.filter(Q(lien_verifie_le__isnull=True) | Q(lien_verifie_le__lt=limite))
        elif not o["toutes"]:
            lot = lot.filter(lien_verifie_le__isnull=True)
        offres = list(lot.order_by("source", "id").values("id", "source", "titre", "lien"))
        if not offres:
            self.stdout.write("Aucune offre a verifier.")
            return

        par_source = Counter(x["source"] for x in offres)
        duree = sum(DELAIS.get(s, DELAI_PAR_DEFAUT) * n for s, n in par_source.items())
        self.stdout.write(f"{len(offres)} offre(s) a verifier : {dict(par_source)}")
        self.stdout.write(f"Duree minimale (delais de politesse) : {duree / 60:.0f} min.\n")

        verdicts = Counter()
        precedente = None
        for i, offre in enumerate(offres, start=1):
            # Delai par source : la BAD, le WWF et MNP imposent Crawl-delay: 10.
            if offre["source"] == precedente:
                time.sleep(DELAIS.get(offre["source"], DELAI_PAR_DEFAUT))
            precedente = offre["source"]

            etat, pourquoi = verifier(offre)
            verdicts[etat] += 1
            if not o["a_blanc"]:
                # Ecrit au fil de l'eau : une passe coupee ne perd rien.
                Offre.objects.filter(pk=offre["id"]).update(
                    lien_etat=etat, lien_verifie_le=timezone.now())
            if etat != OUVERTE:
                self.stdout.write(f"  [{etat:11}] {offre['source']:14} {offre['titre'][:52]}")
                if pourquoi:
                    self.stdout.write(f"                {pourquoi[:110]}")
            if i % 25 == 0:
                self.stdout.write(f"  ... {i}/{len(offres)} — {dict(verdicts)}")

        self.stdout.write(f"\nVerdicts : {dict(verdicts)}")
        if o["a_blanc"]:
            self.stdout.write("Passage a blanc : rien n'a ete ecrit.")
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{verdicts[INTROUVABLE] + verdicts[CLOSE]} offre(s) retiree(s) des actionnables."))
