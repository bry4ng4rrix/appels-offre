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
            self.assertContains(page, "soit 43&nbsp;Ar")  # 65 000 Ar / (50 x 30 jours)
