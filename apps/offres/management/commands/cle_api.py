"""Gestion des jetons d'acces a l'API.

    manage.py cle_api --creer "tableau de bord"
    manage.py cle_api --lister
    manage.py cle_api --revoquer "tableau de bord"

Le jeton n'est affiche QU'UNE FOIS, a la creation : seule son empreinte est
conservee. Perdu, il se remplace, il ne se retrouve pas.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.offres.auth import empreinte, engendrer
from apps.offres.models import CleApi


class Command(BaseCommand):
    help = "Cree, liste ou revoque un jeton d'acces a l'API."

    def add_arguments(self, parser):
        groupe = parser.add_mutually_exclusive_group(required=True)
        groupe.add_argument("--creer", metavar="NOM",
                            help="cree un jeton et l'affiche une seule fois")
        groupe.add_argument("--lister", action="store_true",
                            help="liste les jetons, sans jamais les afficher")
        groupe.add_argument("--revoquer", metavar="NOM",
                            help="rend un jeton inutilisable, sans le supprimer")

    def handle(self, *args, **options):
        if options["creer"]:
            return self.creer(options["creer"])
        if options["revoquer"]:
            return self.revoquer(options["revoquer"])
        return self.lister()

    def creer(self, nom: str):
        nom = nom.strip()
        if not nom:
            raise CommandError("Le nom ne peut pas etre vide.")
        if CleApi.objects.filter(nom=nom).exists():
            raise CommandError(f"Une cle nommee {nom!r} existe deja.")

        jeton = engendrer()
        CleApi.objects.create(nom=nom, empreinte=empreinte(jeton))

        self.stdout.write(self.style.SUCCESS(f"\nCle {nom!r} creee.\n"))
        self.stdout.write(f"  {jeton}\n")
        self.stdout.write(self.style.WARNING(
            "\nNotez-le maintenant : seule son empreinte est conservee, "
            "il ne sera plus affiche.\n"))
        # Sur une seule ligne : une continuation de shell se recopie mal
        # entre PowerShell, cmd et bash, qui n'ont pas le meme caractere.
        self.stdout.write(
            "Usage :\n"
            f'  curl -H "Authorization: Bearer {jeton}" '
            "http://127.0.0.1:8000/api/statistiques/\n")

    def revoquer(self, nom: str):
        cle = CleApi.objects.filter(nom=nom.strip()).first()
        if cle is None:
            raise CommandError(f"Aucune cle nommee {nom!r}.")
        if cle.revoque_le:
            self.stdout.write(f"{nom!r} etait deja revoquee "
                              f"le {cle.revoque_le:%Y-%m-%d %H:%M}.")
            return
        # La ligne est conservee : elle dit qu'un acces a existe, et empeche
        # de reutiliser le meme nom par inadvertance.
        cle.revoque_le = timezone.now()
        cle.save(update_fields=["revoque_le"])
        self.stdout.write(self.style.SUCCESS(f"{nom!r} revoquee."))

    def lister(self):
        cles = CleApi.objects.all()
        if not cles:
            self.stdout.write("Aucune cle. L'API refuse donc tout appel.\n"
                              'Creez-en une : manage.py cle_api --creer "mon usage"')
            return
        self.stdout.write(f"{'NOM':28} {'ETAT':10} {'CREEE':12} DERNIER USAGE")
        for cle in cles:
            usage = (f"{cle.derniere_utilisation:%Y-%m-%d %H:%M}"
                     if cle.derniere_utilisation else "jamais")
            etat = "active" if cle.active else "revoquee"
            self.stdout.write(f"{cle.nom[:28]:28} {etat:10} "
                              f"{cle.cree_le:%Y-%m-%d}   {usage}")
