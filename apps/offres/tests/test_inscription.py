"""Inscription par l'API headless : essai gratuit, un compte par appareil, IP deja vue sans essai."""

import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.offres.models import Inscription


class Inscriptions(TestCase):

    def inscrire(self, email, ip="41.1.1.1", appareil="appareil-a", **extra):
        # Le frontend Next appelle depuis le reseau interne (127.0.0.1 ici) et passe l'origine du visiteur.
        return self.client.post("/_allauth/app/v1/auth/signup",
                                json.dumps({"email": email, "password": "mdp-de-test-1234"}),
                                content_type="application/json",
                                HTTP_X_CLIENT_IP=ip, HTTP_X_APPAREIL=appareil, **extra)

    def test_nouveau_compte_14_jours_d_essai_et_empreintes_pas_en_clair(self):
        self.assertEqual(self.inscrire("a@exemple.org").status_code, 200)
        i = Inscription.objects.get(user__email="a@exemple.org")
        self.assertEqual(i.essai_jusqu_au, timezone.localdate() + timedelta(days=13))
        self.assertEqual(len(i.ip), 64)
        self.assertNotIn("41.1.1.1", i.ip)

    def test_meme_appareil_refuse(self):
        self.inscrire("a@exemple.org")
        refus = self.inscrire("b@exemple.org", ip="41.2.2.2")
        self.assertEqual(refus.status_code, 400, refus.content)
        self.assertEqual(refus.json()["errors"][0]["code"], "appareil_deja_utilise")
        self.assertFalse(get_user_model().objects.filter(email="b@exemple.org").exists())

    def test_meme_ip_compte_cree_sans_essai(self):
        self.inscrire("a@exemple.org")
        self.assertEqual(self.inscrire("b@exemple.org", appareil="appareil-b").status_code, 200)
        self.assertIsNone(Inscription.objects.get(user__email="b@exemple.org").essai_jusqu_au)

    def test_en_tetes_ignores_depuis_internet(self):
        # Appel direct depuis une adresse publique : X-Appareil et X-Client-Ip ne sont pas crus.
        self.inscrire("a@exemple.org", REMOTE_ADDR="8.8.8.8")
        reponse = self.inscrire("b@exemple.org", ip="41.9.9.9", REMOTE_ADDR="8.8.4.4")
        self.assertEqual(reponse.status_code, 200, reponse.content)
        b = Inscription.objects.get(user__email="b@exemple.org")
        self.assertEqual(b.appareil, "")
        self.assertIsNotNone(b.essai_jusqu_au)  # IP reelle 8.8.4.4 : nouvelle
