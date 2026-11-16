from django.test import SimpleTestCase

from apps.offres.services.taxonomie import code_secteur


class CodesSecteurs(SimpleTestCase):

    def test_variantes_electricite_rejoignent_energie(self):
        for nom in ("Electrical", "Électricité", "electricity", "Energy"):
            with self.subTest(nom=nom):
                self.assertEqual(code_secteur(nom), "energie")

    def test_ecologie_rejoint_environnement(self):
        for nom in ("Écologie", "Ecology"):
            with self.subTest(nom=nom):
                self.assertEqual(code_secteur(nom), "environnement")

    def test_un_secteur_inconnu_reste_disponible(self):
        self.assertEqual(code_secteur("Santé animale"), "sante_animale")
