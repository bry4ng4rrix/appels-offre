"""Cree un administrateur, ou promeut un compte existant.

    manage.py creer_admin --email admin@exemple.org
    docker compose exec web python manage.py creer_admin --email admin@exemple.org

Seul chemin vers le role ADMIN : aucune page ne permet de s'inscrire admin.
Le mot de passe est demande deux fois au clavier, jamais en argument (il
finirait dans l'historique du shell). Pour un script sans terminal, il peut
venir de la variable CREER_ADMIN_MOT_DE_PASSE. L'email est marque verifie :
l'admin se connecte sans attendre de lien.
"""

import os
from getpass import getpass

from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction


class Command(BaseCommand):
    help = "Crée un administrateur (ou promeut un compte existant)."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)

    def handle(self, *args, **o):
        email = o["email"].strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            raise CommandError(f"Adresse invalide : {email}")

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(email=email, username=get_adapter().generate_unique_username([email]))

        mot_de_passe = os.environ.get("CREER_ADMIN_MOT_DE_PASSE") or self.demander()
        try:
            validate_password(mot_de_passe, user)
        except ValidationError as exc:
            raise CommandError("Mot de passe refusé : " + " ".join(exc.messages))

        with transaction.atomic():
            cree = user.pk is None
            user.is_staff = user.is_superuser = user.is_active = True
            user.set_password(mot_de_passe)
            user.save()
            EmailAddress.objects.filter(user=user).exclude(email__iexact=email).update(primary=False)
            EmailAddress.objects.update_or_create(
                user=user, email=email, defaults={"verified": True, "primary": True})

        self.stdout.write(self.style.SUCCESS(
            f"Administrateur {'créé' if cree else 'promu'} : {email}"))

    def demander(self) -> str:
        premier = getpass("Mot de passe : ")
        if premier != getpass("Encore une fois : "):
            raise CommandError("Les deux saisies diffèrent.")
        return premier
