from django.test import SimpleTestCase, TestCase

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

    def test_traductions_et_adjectifs_rejoignent_un_seul_secteur(self):
        for nom in ("Administrative and support", "Administrative et support",
                    "Administration et support"):
            with self.subTest(nom=nom):
                self.assertEqual(code_secteur(nom), "administration_et_support")
        for nom in ("Agriculture et rural", "Agricultural"):
            with self.subTest(nom=nom):
                self.assertEqual(code_secteur(nom), "agriculture")

    def test_un_secteur_inconnu_reste_disponible(self):
        self.assertEqual(code_secteur("Santé animale"), "sante_animale")


class SecteursCourts(TestCase):

    def test_code_limite_a_trois_mots_sans_repetition(self):
        from apps.offres.services.taxonomie import code_secteur
        self.assertEqual(code_secteur(
            "Autres services clients services clients activities services publics services tec"),
            "autres_services_clients")
        self.assertEqual(code_secteur("eau_et_assainissement"), "eau_et_assainissement")
        self.assertEqual(code_secteur("santeur_santeur_et_securite"), "santeur_et_securite")

    def test_raccourcir_rattache_les_offres(self):
        from apps.offres.models import Offre, Secteur
        from apps.offres.services.taxonomie import raccourcir_secteurs
        Secteur.objects.create(code="autres_services_clients", nom="Autres services clients")
        Secteur.objects.create(code="autres_services_clients_services_clients_activities",
                               nom="Autres services clients services clients activities")
        Secteur.objects.create(code="services_tech_services_tech_publics", nom="long")
        Offre.objects.create(id="o1", source="s", titre="t", nature="marche",
                             secteur="autres_services_clients_services_clients_activities")
        Offre.objects.create(id="o2", source="s", titre="t", nature="emploi",
                             secteur="services_tech_services_tech_publics")
        self.assertEqual(raccourcir_secteurs(Secteur, Offre), 2)
        codes = set(Secteur.objects.values_list("code", flat=True))
        self.assertTrue({"autres_services_clients", "services_tech_publics"} <= codes)
        self.assertFalse(any(len(c.split("_")) > 3 for c in codes), codes)
        self.assertEqual(Offre.objects.get(id="o1").secteur, "autres_services_clients")
        o2 = Offre.objects.get(id="o2")
        self.assertEqual((o2.secteur, o2.categorie), ("services_tech_publics", "Services tech publics - Emploi"))
        self.assertEqual(Secteur.objects.get(code="services_tech_publics").nom, "Services tech publics")

    def test_fusion_garde_le_choix_des_profils(self):
        from django.contrib.auth import get_user_model
        from apps.offres.models import Offre, Profil, Secteur
        from apps.offres.services.taxonomie import raccourcir_secteurs
        canon = Secteur.objects.create(code="administration_et_support", nom="Administration et support")
        doublon = Secteur.objects.create(code="administrative_and_support", nom="Administrative and support")
        user = get_user_model().objects.create_user("p", email="p@exemple.org", password="x-1234567")
        profil = Profil.objects.create(user=user)
        profil.secteurs.add(doublon)
        Offre.objects.create(id="o1", source="s", titre="t", secteur="administrative_and_support")
        raccourcir_secteurs(Secteur, Offre)
        self.assertFalse(Secteur.objects.filter(pk=doublon.pk).exists())
        self.assertEqual(list(profil.secteurs.all()), [canon])
        self.assertEqual(Offre.objects.get(id="o1").secteur, "administration_et_support")
