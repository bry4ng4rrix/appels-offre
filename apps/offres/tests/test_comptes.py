"""Comptes : inscription, connexion, Google, roles ADMIN / USER.

Aucun appel reseau : l'echange de code et le decodage du jeton Google sont simules.
"""

import os
import re
from unittest import mock
from urllib.parse import parse_qs, urlparse

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.offres.models import Offre
from apps.offres.tests.outils import connecter

User = get_user_model()
MDP = "Un-mot-de-passe-solide-42"
GOOGLE = {"google": {"APPS": [{"client_id": "id-de-test", "secret": "secret-de-test"}],
                     "SCOPE": ["openid", "profile", "email"]}}


def lien(message) -> str:
    return re.search(r"https?://\S+", message.body).group(0)


def compte_verifie(email, **champs):
    user = User.objects.create_user(email.split("@")[0], email=email, password=MDP, **champs)
    EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
    return user


class Inscription(TestCase):

    def test_inscription_donne_acces_tout_de_suite(self):
        """Verification coupee tant que l'email n'est pas configure (settings.py)."""
        self.client.post("/comptes/signup/", {
            "email": "direct@exemple.org", "password1": MDP, "password2": MDP})
        self.assertFalse(User.objects.get(email="direct@exemple.org").is_staff)
        self.assertEqual(self.client.get("/offres/").status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_inscription_puis_verification_de_l_email(self):
        reponse = self.client.post("/comptes/signup/", {
            "email": "nouveau@exemple.org", "password1": MDP, "password2": MDP})
        self.assertEqual(reponse.status_code, 302)
        user = User.objects.get(email="nouveau@exemple.org")
        self.assertFalse(user.is_staff)
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        # Pas d'acces avant la verification.
        self.assertEqual(self.client.get("/offres/").status_code, 302)

        self.assertEqual(len(mail.outbox), 1)
        confirmation = urlparse(lien(mail.outbox[0])).path
        self.assertEqual(self.client.get(confirmation).status_code, 200)  # GET ne valide rien
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.client.post(confirmation)
        self.assertTrue(EmailAddress.objects.get(user=user).verified)
        self.assertEqual(self.client.get("/offres/").status_code, 200)

    def test_l_inscription_ne_donne_jamais_le_role_admin(self):
        self.client.post("/comptes/signup/", {
            "email": "malin@exemple.org", "password1": MDP, "password2": MDP,
            "is_staff": "on", "is_superuser": "on"})
        user = User.objects.get(email="malin@exemple.org")
        self.assertFalse(user.is_staff or user.is_superuser)

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_les_emails_partent_par_le_serveur_configure(self):
        faux = mock.Mock()
        with mock.patch("apps.offres.services.notification.NotificationService.configuration",
                        return_value=(faux, "veille@exemple.org", [])):
            self.client.post("/comptes/signup/", {
                "email": "x@exemple.org", "password1": MDP, "password2": MDP})
        (message,), = faux.send_messages.call_args.args
        self.assertEqual((message.to, message.from_email), (["x@exemple.org"], "veille@exemple.org"))


class TableauDEcheances(TestCase):
    """La page de connexion montre quelques offres réelles, rien de non rediffusable."""

    @override_settings(API_PUBLIQUE_SOURCES_EXCLUES=["unjobnet"])
    def test_offres_ouvertes_seulement_et_sources_exclues_absentes(self):
        from datetime import timedelta
        from django.utils import timezone
        dans = lambda j: timezone.now().date() + timedelta(days=j)
        Offre.objects.create(id="a", source="armp", titre="Fourniture de serveurs", pays="Madagascar", date_limite=dans(5))
        Offre.objects.create(id="b", source="unjobnet", titre="Poste confidentiel", pays="Kenya", date_limite=dans(5))
        Offre.objects.create(id="c", source="armp", titre="Offre close", pays="Bénin", date_limite=dans(-1))
        page = self.client.get("/comptes/login/")
        self.assertContains(page, "Fourniture de serveurs")
        self.assertContains(page, "J-5")
        self.assertNotContains(page, "Poste confidentiel")
        self.assertNotContains(page, "Offre close")


class Connexion(TestCase):

    def setUp(self):
        compte_verifie("membre@exemple.org")

    def test_connexion_par_email_puis_deconnexion(self):
        reponse = self.client.post("/comptes/login/", {"login": "membre@exemple.org", "password": MDP})
        # Un USER arrive sur ses suggestions (un admin sur la liste complete).
        self.assertRedirects(reponse, "/pour-vous/", fetch_redirect_response=False)
        self.assertEqual(self.client.get("/offres/").status_code, 200)
        self.client.post("/comptes/logout/")
        self.assertEqual(self.client.get("/offres/").status_code, 302)

    def test_mauvais_mot_de_passe(self):
        reponse = self.client.post("/comptes/login/", {"login": "membre@exemple.org", "password": "faux"})
        self.assertEqual(reponse.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_trop_d_echecs_bloquent_le_compte_un_moment(self):
        for _ in range(5):
            self.client.post("/comptes/login/", {"login": "membre@exemple.org", "password": "faux"})
        self.client.post("/comptes/login/", {"login": "membre@exemple.org", "password": MDP})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_reinitialisation_du_mot_de_passe(self):
        self.client.post("/comptes/password/reset/", {"email": "membre@exemple.org"})
        self.assertEqual(len(mail.outbox), 1)
        formulaire = self.client.get(urlparse(lien(mail.outbox[0])).path, follow=True)
        nouveau = "Encore-plus-solide-2026"
        self.client.post(formulaire.redirect_chain[-1][0] if formulaire.redirect_chain
                         else urlparse(lien(mail.outbox[0])).path,
                         {"password1": nouveau, "password2": nouveau})
        self.assertTrue(User.objects.get(email="membre@exemple.org").check_password(nouveau))


@override_settings(SOCIALACCOUNT_PROVIDERS=GOOGLE)
class ConnexionGoogle(TestCase):

    def connexion_google(self, **revendications):
        donnees = {"sub": "1234567890", "email": "jean@gmail.com", "email_verified": True,
                   "given_name": "Jean", "family_name": "Rakoto",
                   "picture": "https://lh3.googleusercontent.com/photo"} | revendications
        depart = self.client.post("/comptes/google/login/?process=login")
        cible = urlparse(depart["Location"])
        self.assertEqual(cible.netloc, "accounts.google.com")
        parametres = parse_qs(cible.query)
        self.assertEqual(parametres["client_id"], ["id-de-test"])
        self.assertTrue(parametres["redirect_uri"][0].endswith("/comptes/google/login/callback/"))
        with mock.patch.object(OAuth2Client, "get_access_token",
                               return_value={"access_token": "a", "id_token": "j", "expires_in": 3600}), \
             mock.patch.object(GoogleOAuth2Adapter, "_decode_id_token", return_value=donnees):
            return self.client.get("/comptes/google/login/callback/",
                                   {"code": "c", "state": parametres["state"][0]})

    def test_premiere_connexion_cree_un_compte_user(self):
        self.connexion_google()
        user = User.objects.get(email="jean@gmail.com")
        self.assertEqual((user.first_name, user.last_name, user.is_staff), ("Jean", "Rakoto", False))
        self.assertTrue(EmailAddress.objects.get(user=user).verified)
        self.assertEqual(SocialAccount.objects.get(user=user).extra_data["picture"],
                         "https://lh3.googleusercontent.com/photo")
        self.assertEqual(self.client.get("/offres/").status_code, 200)

    def test_un_compte_existant_au_meme_email_verifie_est_relie(self):
        existant = compte_verifie("jean@gmail.com")
        self.connexion_google()
        self.assertEqual(User.objects.filter(email="jean@gmail.com").count(), 1)
        self.assertEqual(SocialAccount.objects.get(provider="google").user, existant)

    def test_un_email_non_verifie_par_google_ne_relie_rien(self):
        existant = compte_verifie("jean@gmail.com")
        self.connexion_google(email_verified=False)
        self.assertFalse(SocialAccount.objects.filter(user=existant).exists())
        self.assertNotEqual(self.client.session.get("_auth_user_id"), str(existant.pk))


class Roles(TestCase):
    """Le serveur refuse : masquer un bouton ne suffit pas."""

    ADMIN_GET = ["/taches/", "/parametres/", "/actions/etat/"]
    ADMIN_POST = ["/actions/lancer/veille/", "/offre/o-1/dater/", "/offre/o-1/decider/",
                  "/parametres/email/", "/parametres/email/tester/", "/taches/cles/creer/",
                  "/parametres/secteurs/creer/", "/parametres/pays/creer/",
                  "/actions/global/suspendre/"]

    def setUp(self):
        Offre.objects.create(id="o-1", source="test", titre="Offre", pertinent=True)

    def test_un_user_n_accede_a_aucune_fonction_admin(self):
        connecter(self.client, admin=False)
        for url in self.ADMIN_GET:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        for url in self.ADMIN_POST:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, {"statut": "gagne", "nom": "x"}).status_code, 403)
        self.assertFalse(Offre.objects.get(pk="o-1").date_limite)

    def test_un_user_consulte_les_offres_sans_les_menus_admin(self):
        connecter(self.client, admin=False)
        for url in ("/offres/", "/offre/o-1/", "/carte/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        page = self.client.get("/offres/")
        self.assertNotContains(page, 'href="/parametres/"')
        self.assertNotContains(page, "Modifier l'échéance")

    def test_un_admin_accede_a_tout(self):
        connecter(self.client)
        for url in self.ADMIN_GET + ["/offres/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get("/offres/"), 'href="/parametres/"')

    def test_un_admin_desactive_perd_l_acces(self):
        admin = connecter(self.client)
        admin.is_active = False
        admin.save()
        self.assertEqual(self.client.get("/parametres/").status_code, 302)


class CreerAdmin(TestCase):

    def test_creer_puis_se_connecter_sans_lien_de_verification(self):
        with mock.patch.dict(os.environ, {"CREER_ADMIN_MOT_DE_PASSE": MDP}):
            call_command("creer_admin", "--email", "Chef@Exemple.org", stdout=mock.Mock())
        admin = User.objects.get(email="chef@exemple.org")
        self.assertTrue(admin.is_staff and admin.is_superuser)
        self.client.post("/comptes/login/", {"login": "chef@exemple.org", "password": MDP})
        self.assertEqual(self.client.get("/parametres/").status_code, 200)

    def test_promouvoir_un_compte_existant(self):
        compte_verifie("membre@exemple.org")
        with mock.patch.dict(os.environ, {"CREER_ADMIN_MOT_DE_PASSE": MDP}):
            call_command("creer_admin", "--email", "membre@exemple.org", stdout=mock.Mock())
        self.assertEqual(User.objects.filter(email="membre@exemple.org").count(), 1)
        self.assertTrue(User.objects.get(email="membre@exemple.org").is_staff)

    def test_mot_de_passe_faible_refuse(self):
        with mock.patch.dict(os.environ, {"CREER_ADMIN_MOT_DE_PASSE": "1234"}), \
             self.assertRaises(CommandError):
            call_command("creer_admin", "--email", "chef@exemple.org")
        self.assertFalse(User.objects.filter(email="chef@exemple.org").exists())
