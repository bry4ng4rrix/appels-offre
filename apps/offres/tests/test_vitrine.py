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
        self.assertContains(page, "27 offres</strong> collectées,")
        self.assertContains(page, "Se connecter pour voir les autres offres disponibles")
        self.assertNotContains(page, "https://exemple.org/")
        self.assertContains(page, "/comptes/login/?next=/")

    def test_connecte_l_accueil_est_la_liste_des_offres(self):
        offre("u1", 2)
        connecter(self.client, admin=False)
        self.assertRedirects(self.client.get("/"), "/offres/")
        page = self.client.get("/offres/")
        self.assertNotContains(page, ">Offres</a>")
        self.assertContains(page, ">Accueil</a>", count=1)
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


class Referencement(TestCase):
    """SEO / AEO : seules les pages publiques s'ouvrent aux moteurs."""

    def test_accueil_balise_pour_les_moteurs(self):
        offre("x1", 2)
        Offre.objects.filter(pk="x1").update(titre="Piège </script><b>")
        page = self.client.get("/")
        self.assertContains(page, '<meta name="robots" content="index, follow')
        self.assertContains(page, '<link rel="canonical" href="http://testserver/">')
        self.assertContains(page, '"@type": "FAQPage"')
        self.assertContains(page, "Questions fréquentes")
        # Un titre de source ne doit jamais fermer la balise JSON-LD.
        ld = page.content.decode().split('application/ld+json">', 1)[1].split("</script>", 1)[0]
        self.assertIn("\\u003c/script\\u003e", ld)

    def test_pages_privees_et_connexion_hors_index(self):
        self.assertContains(self.client.get("/comptes/login/"), '<meta name="robots" content="noindex">')
        connecter(self.client, admin=False)
        self.assertContains(self.client.get("/offres/"), '<meta name="robots" content="noindex">')

    def test_robots_sitemap_llms_publics(self):
        robots = self.client.get("/robots.txt").content.decode()
        self.assertIn("Disallow: /\n", robots)
        self.assertIn("Sitemap: http://testserver/sitemap.xml", robots)
        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap["Content-Type"], "application/xml; charset=utf-8")
        self.assertContains(sitemap, "<loc>http://testserver/carte/</loc>")
        self.assertContains(self.client.get("/llms.txt"), "# Label Collectes")


class Lisibilite(TestCase):

    def test_titre_en_majuscules_passe_en_casse_de_phrase(self):
        from apps.offres.views_web import titre_lisible
        self.assertEqual(titre_lisible("LIVESTOCK FARMING PROMOTION – SUPPLY RFP-2026/014"),
                         "Livestock farming promotion – supply RFP-2026/014")
        self.assertEqual(titre_lisible("Director, Direct Equity Department"),
                         "Director, Direct Equity Department")
        self.assertEqual(titre_lisible("ONU"), "ONU")  # trop court pour juger

    def test_carte_affiche_le_nom_de_la_source(self):
        Offre.objects.create(id="g1", source="grants_gov", titre="SPECIALTY CROP GRANT PROGRAM",
                             pertinent=True, date_limite=timezone.now().date() + timedelta(days=2))
        page = self.client.get("/")
        self.assertContains(page, "Grants.gov (Etats-Unis)")
        self.assertContains(page, "Specialty crop grant program")
        self.assertNotContains(page, ">grants_gov<")
