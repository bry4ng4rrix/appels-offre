"""Limite de consultation des annonces officielles : 10 offres differentes par jour."""

from django.test import TestCase
from django.urls import reverse

from apps.offres.models import Consultation, Offre
from apps.offres.tests.outils import connecter


def offres(n):
    return [Offre.objects.create(id=f"t-{i}", source="test", titre=f"Offre {i}",
                                 lien=f"https://exemple.org/{i}") for i in range(n)]


class Limite(TestCase):

    def consulter(self, offre):
        return self.client.post(reverse("web-consulter", args=[offre.pk]))

    def test_dix_offres_puis_refus_et_meme_offre_gratuite(self):
        user = connecter(self.client, admin=False)
        lot = offres(Consultation.LIMITE_JOUR + 1)
        for o in lot[:-1]:
            self.assertEqual(self.consulter(o)["Location"], o.lien)
        self.assertEqual(self.consulter(lot[0])["Location"], lot[0].lien)  # deja ouverte : gratuite
        self.assertEqual(Consultation.restantes(user), 0)
        refus = self.consulter(lot[-1])
        self.assertEqual(refus["Location"], reverse("web-detail", args=[lot[-1].pk]))
        self.assertEqual(Consultation.objects.filter(user=user).count(), Consultation.LIMITE_JOUR)

    def test_compteur_dans_l_en_tete(self):
        connecter(self.client, admin=False)
        o = offres(1)[0]
        self.consulter(o)
        page = self.client.get(reverse("web-detail", args=[o.pk]))
        self.assertContains(page, '<span id="credits">9</span>')

    def test_admin_sans_limite(self):
        connecter(self.client)
        for o in offres(Consultation.LIMITE_JOUR + 1):
            self.assertEqual(self.consulter(o)["Location"], o.lien)
        self.assertFalse(Consultation.objects.exists())


class Abonnements(TestCase):
    """Plans de la migration 0022 : Standard (lot de 20), Mensuel (+50/jour, 30 j)."""

    def setUp(self):
        from apps.offres.models import Plan
        self.user = connecter(self.client, admin=False)
        self.standard = Plan.objects.get(nom="Standard")
        self.mensuel = Plan.objects.get(nom="Mensuel")

    def demander_et_valider(self, plan):
        from apps.offres.models import Abonnement
        self.client.post(reverse("web-abonnement"), {"plan": plan.pk})
        demande = Abonnement.objects.get(user=self.user, plan=plan)
        self.assertEqual(demande.statut, Abonnement.EN_ATTENTE)
        self.assertEqual(Consultation.restantes(self.user), Consultation.LIMITE_JOUR)  # rien avant validation
        demande.valider(self.user)
        return demande

    def test_lot_utilise_apres_les_credits_du_jour(self):
        lot = self.demander_et_valider(self.standard)
        self.assertEqual(Consultation.restantes(self.user), 30)
        for o in offres(Consultation.LIMITE_JOUR + 3):
            self.assertTrue(Consultation.debiter(self.user, o))
        lot.refresh_from_db()
        self.assertEqual(lot.credits_restants, 17)
        self.assertEqual(Consultation.restantes(self.user), 17)

    def test_plan_par_jour_ajoute_au_quota(self):
        demande = self.demander_et_valider(self.mensuel)
        self.assertEqual(Consultation.restantes(self.user), 60)
        self.assertEqual((demande.fin - demande.debut).days, 29)

    def test_une_seule_demande_en_attente(self):
        from apps.offres.models import Abonnement
        self.client.post(reverse("web-abonnement"), {"plan": self.standard.pk})
        self.client.post(reverse("web-abonnement"), {"plan": self.mensuel.pk})
        self.assertEqual(Abonnement.objects.filter(user=self.user).count(), 1)
        self.assertContains(self.client.get(reverse("web-abonnement")), "65\u00a0000")  # separateur francais : espace insecable


class Explications(TestCase):

    def test_credits_et_plans_sous_la_faq_et_sous_la_carte(self):
        for url in (reverse("public-vitrine"), reverse("web-carte")):
            page = self.client.get(url)
            self.assertContains(page, "Crédits et abonnements")
            self.assertContains(page, "+50")
            self.assertContains(page, "Soit 43&nbsp;Ar le crédit")  # 65 000 Ar / (50 x 30 jours)


class GestionAbonnements(TestCase):
    """Page Abonnements (ADMIN) : valider ou refuser les demandes, gérer les plans."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from apps.offres.models import Abonnement, Plan
        self.membre = get_user_model().objects.create_user("client", email="client@exemple.org")
        self.mensuel = Plan.objects.get(nom="Mensuel")
        self.demande = Abonnement.objects.create(user=self.membre, plan=self.mensuel)

    def test_reservee_aux_admins_et_absente_du_menu_des_membres(self):
        connecter(self.client, admin=False)
        self.assertEqual(self.client.get(reverse("web-abonnements")).status_code, 403)
        url = reverse("web-abonnement-decider", args=[self.demande.pk, "valider"])
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertNotContains(self.client.get(reverse("web-liste")), reverse("web-abonnements"))

    def test_valider_puis_refuser(self):
        from apps.offres.models import Abonnement
        admin = connecter(self.client)
        page = self.client.get(reverse("web-abonnements"))
        self.assertContains(page, "client@exemple.org")
        self.assertContains(page, 'title="Demandes en attente">1<')  # pastille du menu
        self.client.post(reverse("web-abonnement-decider", args=[self.demande.pk, "valider"]))
        self.demande.refresh_from_db()
        self.assertEqual((self.demande.statut, self.demande.valide_par), (Abonnement.VALIDE, admin))
        self.assertEqual(Consultation.restantes(self.membre), Consultation.LIMITE_JOUR + 50)
        # Deja traitee : ni revalidee ni refusee.
        url = reverse("web-abonnement-decider", args=[self.demande.pk, "refuser"])
        self.assertEqual(self.client.post(url).status_code, 404)
        autre = Abonnement.objects.create(user=self.membre, plan=self.mensuel)
        self.client.post(reverse("web-abonnement-decider", args=[autre.pk, "refuser"]))
        autre.refresh_from_db()
        self.assertEqual(autre.statut, Abonnement.REFUSE)
        self.assertContains(self.client.get(reverse("web-abonnements") + "?statut=refuse"), "Refusé</span>")

    def test_creer_et_modifier_un_plan(self):
        from apps.offres.models import Plan
        connecter(self.client)
        self.client.post(reverse("web-plan-creer"), {
            "nouveau-nom": "Annuel", "nouveau-prix": "500000", "nouveau-credits": "100",
            "nouveau-par_jour": "on", "nouveau-duree_jours": "365", "nouveau-actif": "on"})
        self.assertTrue(Plan.objects.filter(nom="Annuel", duree_jours=365, actif=True).exists())
        p = f"p{self.mensuel.pk}"
        self.client.post(reverse("web-plan-modifier", args=[self.mensuel.pk]), {
            f"{p}-nom": "Mensuel", f"{p}-prix": "70000", f"{p}-credits": "0", f"{p}-duree_jours": "30"})
        self.mensuel.refresh_from_db()
        self.assertEqual(self.mensuel.prix, 65000)  # 0 credit refuse : rien n'est enregistre
        self.client.post(reverse("web-plan-modifier", args=[self.mensuel.pk]), {
            f"{p}-nom": "Mensuel", f"{p}-prix": "70000", f"{p}-credits": "50", f"{p}-duree_jours": "30"})
        self.mensuel.refresh_from_db()
        self.assertEqual((self.mensuel.prix, self.mensuel.actif), (70000, False))  # case decochee = retire
