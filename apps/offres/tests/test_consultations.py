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
