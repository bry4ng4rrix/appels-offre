"""Moteur de regles : cas reels repris de l'ancien test_nature.py (tires de la base)."""

from django.test import SimpleTestCase

from apps.offres.services.classifier import RuleBasedClassifier as C

#: (nature attendue, titre, organisation, description)
CAS = [
    # Le piege central : "recrutement" ne tranche rien, les deux cas l'emploient.
    ("emploi", "Avis de recrutement : Comptable pour le projet FSRP-CGIAR",
     "AfricaRice", ""),
    ("marche", "Recrutement d'une firme pour l'accompagnement et le renforcement "
               "organisationnel des organisations paysannes feminines", "FIDA", ""),

    # Marches sans ambiguite.
    ("marche", "Invitation of Bids for Design, Supply, Installation, Configuration, "
               "Testing and Commissioning of a modern, secure and scalable IT "
               "Infrastructure Environment", "Mauritius Tourism Promotion Authority", ""),
    ("marche", "Demande de cotations pour la fourniture de materiel informatique",
     "FID", ""),
    ("marche", "DICT - Acquisition of a Curatelle Information System",
     "Department of Information Communications Technology", ""),

    # Le prefixe entre crochets designe la procedure, pas la nature de ce qui
    # est achete. Une manifestation d'interet de la Banque mondiale porte
    # aussi bien sur un cabinet que sur un consultant individuel : ces quatre
    # cas etaient tous qualifies "marche" avant que le prompt ne le dise.
    ("emploi", "[Request for Expression of Interest] Recrutement d'un(e) Responsable "
               "Administratif et Financier", "Banque mondiale", ""),
    ("emploi", "[Request for Expression of Interest] Assistant regional en "
               "suivi-evaluation", "Banque mondiale", ""),
    ("emploi", "[Request for Expression of Interest] Recrutement de deux Jeunes "
               "Ingenieurs", "Banque mondiale", ""),
    ("marche", "[Request for Expression of Interest] Selection de partenaires de "
               "mise en oeuvre", "Banque mondiale", ""),
    ("marche", "[Invitation for Bids] Acquisition des materiels informatiques et "
               "bureautiques", "Banque mondiale", ""),

    # Postes sans ambiguite, dont un intitule technique qui ressemble a un marche.
    ("emploi", "Public Key Infrastructure (PKI) Engineer (Project Post)",
     "NATO", "Vacancy notice, staff position"),
    ("emploi", "Software Developer - Fixed Term Appointment", "PNUD", "Job vacancy"),
    ("emploi", "Avis de vacance de poste : Chauffeurs", "Africa Rice", ""),
    ("emploi", "Avis de recrutement : Chercheur associe pour le Projet "
               "FSRP-CGIAR_Madagascar", "AfricaRice", ""),
]


class Nature(SimpleTestCase):

    def test_cas_reels(self):
        for attendue, titre, organisation, description in CAS:
            with self.subTest(titre=titre):
                self.assertEqual(C.detecter_nature(titre), attendue)

    def test_unjobnet_ne_publie_que_des_postes(self):
        self.assertEqual(C.detecter_nature("Data analysis", "unjobnet"), "emploi")

    def test_contrat_individuel_est_un_emploi_ecarte(self):
        v = C.evaluer({"titre": "UNDP-IC-2026-214 Developpement d'un logiciel", "pays": "Madagascar"})
        self.assertEqual((v.nature, v.pertinent), ("emploi", False))


class Secteur(SimpleTestCase):

    def secteur(self, titre):
        return C.evaluer({"titre": titre, "pays": "Madagascar"}).secteur

    def test_priorites(self):
        # Un logiciel reste informatique meme s'il parle d'irrigation ;
        # un chateau d'eau reste "eau" meme s'il se construit.
        self.assertEqual(self.secteur("Logiciel de gestion des périmètres irrigués"), "informatique")
        self.assertEqual(self.secteur("Construction d'un château d'eau"), "eau")
        self.assertEqual(self.secteur("Étude d'impact environnemental de la route RN7"), "environnement")
        self.assertEqual(self.secteur("Aménagement hydro-agricole et irrigation"), "agriculture")
        self.assertEqual(self.secteur("Réhabilitation de bâtiments scolaires"), "construction")

    def test_pas_de_faux_positif_dans_un_mot(self):
        # "erp" dans interpretation, "wash" dans Washington, "esia" dans Indonesia.
        for titre in ("Interpretation services", "Conference in Washington", "Indonesia school feeding",
                      "Mise aux normes accessibilité des ERP-6 sites", "ERP de 5e catégorie"):
            with self.subTest(titre=titre):
                self.assertEqual(self.secteur(titre), "autre")

    def test_erp_logiciel_reste_informatique(self):
        self.assertEqual(self.secteur("Mise en oeuvre d'une solution ERP de gestion intégrée"), "informatique")

    def test_accents_et_pluriels(self):
        self.assertEqual(self.secteur("FOURNITURE DE LOGICIELS"), "informatique")
        self.assertEqual(self.secteur("Travaux de réhabilitation des forages"), "eau")


class Pertinence(SimpleTestCase):

    def verdict(self, titre, pays):
        return C.evaluer({"titre": titre, "pays": pays})

    def test_madagascar_tous_secteurs(self):
        self.assertTrue(self.verdict("Construction d'un pont", "Madagascar").pertinent)

    def test_informatique_partout(self):
        self.assertTrue(self.verdict("Development of a website", "Kenya").pertinent)

    def test_terrain_seulement_ocean_indien(self):
        self.assertTrue(self.verdict("Réhabilitation de routes", "La Réunion").pertinent)
        self.assertTrue(self.verdict("Water supply works", "Mauritius").pertinent)
        self.assertFalse(self.verdict("Road rehabilitation", "Senegal").pertinent)

    def test_hors_perimetre(self):
        v = self.verdict("Fourniture de produits pharmaceutiques", "Madagascar")
        self.assertEqual((v.pertinent, v.secteur), (False, "autre"))

    def test_raison_courte(self):
        v = self.verdict("Développement d'une application mobile de gestion " * 5, "Madagascar")
        self.assertLessEqual(len(v.raison), 60)
