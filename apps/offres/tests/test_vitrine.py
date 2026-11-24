"""Vitrine publique /decouvrir/ : visible sans connexion, annonces reservees aux comptes."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.offres.models import Offre
from apps.offres.tests.outils import connecter


def offre(pk, jours, secteur="sante"):
    return Offre.objects.create(
        id=pk, source="test", titre=f"Offre {pk}", pertinent=True, secteur=secteur,
        lien=f"https://exemple.org/{pk}",
        date_limite=timezone.now().date() + timedelta(days=jours))


class Vitrine(TestCase):
    def test_anonyme_voit_les_urgentes_sans_le_lien_officiel(self):
        for i in range(25):
            offre(f"u{i}", 3)
        offre("loin", 40, secteur="eau")
        page = self.client.get("/decouvrir/")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.context["urgentes"]), 20)
        self.assertNotIn("loin", [o.pk for o in page.context["urgentes"]])
        # Le secteur sans urgence a quand meme son offre.
        self.assertIn("loin", [o.pk for o in page.context["par_secteur"]])
        self.assertNotContains(page, "https://exemple.org/")
        self.assertContains(page, "/comptes/login/?next=/decouvrir/")
        self.assertContains(page, "/api/public/carte/points/")

    def test_connecte_garde_les_boutons(self):
        offre("u1", 2)
        connecter(self.client, admin=False)
        page = self.client.get("/decouvrir/")
        self.assertContains(page, 'href="https://exemple.org/u1"')
        self.assertContains(page, "Copier le lien")

    def test_le_reste_exige_toujours_la_connexion(self):
        for url in ("/", "/carte/", "/carte/points/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)
