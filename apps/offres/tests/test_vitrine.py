"""Vitrine publique / : visible sans connexion, annonces reservees aux comptes."""

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
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.context["urgentes"]), 20)
        self.assertNotIn("loin", [o.pk for o in page.context["urgentes"]])
        self.assertNotContains(page, "Offre loin")
        Offre.objects.create(id="vieille", source="test", titre="x", pertinent=True,
                             date_limite=timezone.now().date() - timedelta(days=3))
        page = self.client.get("/")
        self.assertEqual((page.context["disponibles"], page.context["total"]), (26, 27))
        self.assertContains(page, "Se connecter pour voir les autres offres disponibles")
        self.assertNotContains(page, "https://exemple.org/")
        self.assertContains(page, "/comptes/login/?next=/")

    def test_connecte_garde_les_boutons(self):
        offre("u1", 2)
        connecter(self.client, admin=False)
        page = self.client.get("/")
        self.assertContains(page, 'href="https://exemple.org/u1"')
        self.assertNotContains(page, "Copier le lien</button>")

    def test_le_reste_exige_toujours_la_connexion(self):
        for url in ("/offres/", "/carte/points/", "/pour-vous/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)

    def test_carte_publique_sans_connexion(self):
        page = self.client.get("/carte/")
        self.assertTemplateUsed(page, "offres/carte_publique.html")
        self.assertContains(page, "/api/public/carte/points/")
        connecter(self.client, admin=False)
        self.assertTemplateUsed(self.client.get("/carte/"), "offres/carte.html")

    def test_deconnexion_ramene_a_l_accueil(self):
        connecter(self.client, admin=False)
        self.assertRedirects(self.client.post("/comptes/logout/"), "/")


class CopierLeLien(TestCase):
    """Seul un admin voit « Copier le lien », sur la liste comme sur la fiche."""

    def test_reserve_a_l_admin(self):
        offre("c1", 5)
        for admin, attendu in ((False, 0), (True, 1)):
            self.client.logout()
            connecter(self.client, admin=admin)
            for url in ("/offres/", "/offre/c1/"):
                with self.subTest(admin=admin, url=url):
                    self.assertContains(self.client.get(url), "Copier le lien</button>", count=attendu)
