"""Marque de tri (le traitement des 6 h ne retrie que le non trie) et organisation de nuit."""

import io
from collections import Counter
from datetime import datetime, time, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.offres.models import Offre, Parametres, Secteur, Tache
from apps.offres.services.pipeline import PipelineService, construire_offre
from apps.offres.tests.outils import AvecAdmin

FAUX = dict(pertinent=False, nature="marche", secteur="autre", categorie="x", raison="faux")
TITRE_INFO = "Développement d'une application web et maintenance informatique"


class MarqueDeTri(TestCase):

    def test_la_collecte_marque_ses_offres(self):
        offre = construire_offre({"id": "n1", "source": "test", "titre": TITRE_INFO})
        self.assertIsNotNone(offre.trie_le)

    def test_le_tri_marque_tout_ce_qu_il_traite(self):
        Offre.objects.create(id="a", source="test", titre=TITRE_INFO, **FAUX)
        r = PipelineService.requalifier(Offre.objects.all())
        self.assertEqual((r["total"], r["changees"]), (1, 1))
        self.assertIsNotNone(Offre.objects.get(pk="a").trie_le)

    def test_le_traitement_complet_ne_retrie_que_les_offres_sans_marque(self):
        hier = timezone.now() - timedelta(days=1)
        Offre.objects.create(id="deja", source="test", titre=TITRE_INFO, trie_le=hier, **FAUX)
        Offre.objects.create(id="neuve", source="test", titre=TITRE_INFO, **FAUX)
        t = Tache.objects.create(nom="tout", phase=2)
        with mock.patch("apps.offres.management.commands.tout.verifier_offres", return_value=Counter()), \
             mock.patch("apps.offres.services.alertes.traiter",
                        return_value={"creees": 0, "emails": 0, "offres": 0, "echecs": 0}):
            call_command("tout", "--tache", str(t.pk), stdout=mock.MagicMock())
        deja, neuve = Offre.objects.get(pk="deja"), Offre.objects.get(pk="neuve")
        self.assertEqual((deja.secteur, deja.trie_le), ("autre", hier))  # pas retriee
        self.assertEqual(neuve.secteur, "informatique")
        self.assertIsNotNone(neuve.trie_le)
        t.refresh_from_db()
        self.assertIn("1 offre(s) non triée(s) traitée(s)", t.detail)


class OrganisationDeNuit(TestCase):

    def lancer(self, phase=1):
        t = Tache.objects.create(nom="nuit", phase=phase)
        call_command("organiser", "--tache", str(t.pk), stdout=mock.MagicMock())
        t.refresh_from_db()
        return t

    def test_catalogues_ranges(self):
        Offre.objects.create(id="syn", source="test", titre="Panneaux", secteur="electricity",
                             nature="marche", trie_le=timezone.now())
        Offre.objects.create(id="neuf", source="test", titre="Vaccins", secteur="sante_animale",
                             nature="marche", trie_le=timezone.now())
        info = Secteur.objects.get_or_create(code="informatique", defaults={"nom": "Informatique"})[0]
        info.nom = "Numérique"
        info.save()
        Offre.objects.create(id="ren", source="test", titre="Serveurs", secteur="informatique",
                             nature="marche", categorie="Informatique - Marche", trie_le=timezone.now())
        # Anciennes : seule la phase « catalogues » les concerne.
        Offre.objects.update(date_ajout=timezone.now() - timedelta(days=2))
        t = self.lancer()
        self.assertEqual(Offre.objects.get(pk="syn").secteur, "energie")
        self.assertTrue(Secteur.objects.filter(code="sante_animale").exists())
        self.assertEqual(Offre.objects.get(pk="ren").categorie, "Numérique - Marche")
        self.assertEqual(t.statut, Tache.TERMINEE)
        self.assertIn("secteur(s) ajouté(s)", t.detail)

    def test_reclasse_les_nouvelles_et_les_autres_ouvertes_puis_avance_le_repere(self):
        il_y_a_deux_jours = timezone.now() - timedelta(days=2)
        Parametres.objects.update_or_create(pk=1, defaults={"nuit_depuis": timezone.now() - timedelta(hours=1)})
        nouvelle = Offre.objects.create(id="nouvelle", source="test", titre=TITRE_INFO, trie_le=timezone.now(), **FAUX)
        ancienne = Offre.objects.create(id="ancienne", source="test", titre=TITRE_INFO, trie_le=il_y_a_deux_jours,
                                        **{**FAUX, "secteur": "construction"})
        Offre.objects.filter(pk="ancienne").update(date_ajout=il_y_a_deux_jours)
        autre = Offre.objects.create(id="autre", source="test", titre=TITRE_INFO, trie_le=il_y_a_deux_jours, **FAUX)
        Offre.objects.filter(pk="autre").update(date_ajout=il_y_a_deux_jours)
        avant = timezone.now()
        self.lancer()
        self.assertEqual(Offre.objects.get(pk=nouvelle.pk).secteur, "informatique")
        self.assertEqual(Offre.objects.get(pk=autre.pk).secteur, "informatique")      # restee « autre »
        self.assertEqual(Offre.objects.get(pk=ancienne.pk).secteur, "construction")   # ni neuve ni « autre »
        self.assertGreaterEqual(Parametres.charger().nuit_depuis, avant)

    def test_une_reprise_saute_ce_qui_a_deja_ete_reclasse_cette_nuit(self):
        from apps.offres.services.organisation import a_classer
        debut = timezone.now()
        Offre.objects.create(id="faite", source="test", titre="x", trie_le=debut + timedelta(seconds=1), **FAUX)
        Offre.objects.create(id="restante", source="test", titre="y", trie_le=debut - timedelta(hours=1), **FAUX)
        self.assertEqual(list(a_classer(debut).values_list("pk", flat=True)), ["restante"])


class PlanificationDeNuit(TestCase):

    def setUp(self):
        from apps.offres.management.commands.planifier import Command
        self.tz = ZoneInfo("Indian/Antananarivo")
        Parametres.objects.update_or_create(pk=1, defaults={"intervalle_collecte": 6, "heure_nuit": time(2, 0)})
        self.cmd = Command(stdout=io.StringIO())
        self.cmd.heure_imposee, self.cmd.cible, self.cmd.processus = None, None, []
        self.cmd.passage = mock.Mock()
        self.cmd.nuit = mock.Mock(return_value=True)

    def a(self, h, m):
        return datetime(2026, 11, 18, h, m, tzinfo=self.tz)  # un mercredi

    def tour(self, instant):
        with mock.patch("django.utils.timezone.localtime", return_value=instant):
            return self.cmd.tour()

    def test_lancee_a_l_heure_puis_le_lendemain(self):
        self.assertEqual(self.tour(self.a(1, 59)), 60)
        self.cmd.nuit.assert_not_called()
        self.tour(self.a(2, 0))
        self.cmd.nuit.assert_called_once()
        self.assertEqual(self.cmd.cible_nuit, self.a(2, 0) + timedelta(days=1))

    def test_reportee_tant_qu_une_tache_tourne(self):
        self.tour(self.a(1, 59))
        self.cmd.nuit.return_value = False
        self.assertEqual(self.tour(self.a(2, 0)), 60)  # pas de boucle serree
        self.tour(self.a(2, 1))
        self.assertEqual(self.cmd.nuit.call_count, 2)
        self.cmd.nuit.return_value = True
        self.tour(self.a(2, 30))
        self.assertEqual(self.cmd.cible_nuit, self.a(2, 0) + timedelta(days=1))


class ReglageHeureDeNuit(AvecAdmin):

    def test_l_heure_se_regle_dans_les_parametres(self):
        self.client.post("/parametres/", {"intervalle_collecte": "6", "heure_nuit": "03:30"},
                         HTTP_HX_REQUEST="true")
        self.assertEqual(Parametres.charger().heure_nuit, time(3, 30))
        self.assertContains(self.client.get("/taches/"), "Organisation de nuit")
