"""Taches de fond : lancement depuis l'interface, verrou, progression, fin."""

import json
import os
import socket
import tempfile
from collections import Counter
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.offres.models import Offre, Tache
from apps.offres.tests.test_scrapers import FauxScraper, item


def message(reponse):
    return json.loads(reponse["HX-Trigger"])["toast"]["message"]


def faux_popen(pid=os.getpid()):
    """Popen simule : le pid est celui du processus de test, donc vivant."""
    return mock.patch("apps.offres.services.taches.subprocess.Popen",
                      return_value=mock.Mock(pid=pid))


#: Les journaux des taches de test ne vont pas dans le vrai dossier logs/.
DOSSIER_TEMPORAIRE = override_settings(BASE_DIR=Path(tempfile.mkdtemp()))


@DOSSIER_TEMPORAIRE
class Lancement(TestCase):

    def test_lance_la_commande_et_rend_le_panneau(self):
        with faux_popen() as popen:
            reponse = self.client.post("/actions/lancer/tout/", HTTP_HX_REQUEST="true")
        tache = Tache.objects.get()
        self.assertEqual((tache.nom, tache.statut, tache.pid), ("tout", Tache.EN_COURS, os.getpid()))
        commande = popen.call_args.args[0]
        self.assertEqual(commande[-3:], ["tout", "--tache", str(tache.pk)])
        self.assertContains(reponse, 'hx-trigger="every 2s"')
        self.assertEqual(message(reponse), "Traitement complet : démarrage.")

    def test_chaque_bouton_vise_sa_commande(self):
        for nom, commande in (("veille", "veille"), ("trier", "trier"), ("liens", "verifier_liens")):
            Tache.objects.all().delete()
            with self.subTest(nom=nom), faux_popen() as popen:
                self.client.post(f"/actions/lancer/{nom}/")
                self.assertEqual(popen.call_args.args[0][-3], commande)

    def test_une_seule_tache_a_la_fois(self):
        with faux_popen() as popen:
            self.client.post("/actions/lancer/veille/")
            reponse = self.client.post("/actions/lancer/trier/")
        self.assertEqual(popen.call_count, 1)
        self.assertEqual(Tache.objects.count(), 1)
        self.assertEqual(message(reponse), "Déjà en cours : Collecte.")

    def test_action_inconnue_et_get_refuses(self):
        self.assertEqual(self.client.get("/actions/lancer/tout/").status_code, 405)
        with faux_popen() as popen:
            self.client.post("/actions/lancer/rm-rf/")
        popen.assert_not_called()

    def test_une_tache_au_processus_mort_ne_bloque_pas(self):
        Tache.objects.create(nom="veille", hote=socket.gethostname(), pid=2 ** 22 + 12345)
        self.assertIsNone(Tache.active())
        self.assertEqual(Tache.objects.get().statut, Tache.INTERROMPUE)


class Etat(TestCase):

    def test_rien_en_cours(self):
        self.assertEqual(self.client.get("/actions/etat/").content, b"")

    def test_en_cours(self):
        Tache.objects.create(nom="veille", hote=socket.gethostname(), pid=os.getpid(),
                             etape="Collecte : BAD", courant=5, total=22)
        reponse = self.client.get("/actions/etat/")
        self.assertContains(reponse, "Collecte : BAD")
        self.assertContains(reponse, "5 / 22 · 22 %")
        self.assertContains(reponse, "every 2s")

    def test_la_fin_est_annoncee_une_fois_au_panneau_qui_suivait(self):
        t = Tache.objects.create(nom="trier", statut=Tache.TERMINEE, detail="12 verdicts modifiés")
        reponse = self.client.get(f"/actions/etat/?suivi={t.pk}")
        self.assertContains(reponse, "12 verdicts modifiés")
        self.assertNotContains(reponse, "every 2s")
        self.assertEqual(message(reponse), "Tri : terminé.")
        # Une page ouverte plus tard ne reaffiche pas un bilan deja vu.
        self.assertEqual(self.client.get("/actions/etat/").content, b"")

    def test_pastilles_des_phases(self):
        t = Tache(nom="tout", phase=2)
        self.assertEqual(t.phases, [("Collecte", "faite"), ("Tri", "active"), ("Liens", "a_venir")])


@mock.patch("apps.offres.services.pipeline.enrichir_description", return_value="")
@mock.patch("apps.offres.services.pipeline.REGISTRE_SCRAPERS", [FauxScraper])
class ProgressionDesCommandes(TestCase):
    """Les commandes, lancees avec --tache, ecrivent leur avancement en base."""

    def setUp(self):
        FauxScraper.items = [item("p-1", "Développement d'un logiciel"), item("p-2", "Repas")]

    def test_veille(self, *_):
        t = Tache.objects.create(nom="veille")
        call_command("veille", "--sans-notification", "--tache", str(t.pk), stdout=mock.MagicMock())
        t.refresh_from_db()
        self.assertEqual(t.statut, Tache.TERMINEE)
        self.assertIsNotNone(t.fin)
        self.assertIn("1 nouvelle(s) offre(s) retenue(s)", t.detail)

    def test_tout_passe_par_les_trois_phases(self, *_):
        t = Tache.objects.create(nom="tout")
        with mock.patch("apps.offres.management.commands.tout.verifier_offres",
                        return_value=Counter()) as liens:
            call_command("tout", "--sans-notification", "--tache", str(t.pk), stdout=mock.MagicMock())
        t.refresh_from_db()
        self.assertEqual((t.statut, t.phase), (Tache.TERMINEE, 3))
        self.assertEqual(Offre.objects.count(), 2)
        liens.assert_called_once()

    def test_un_echec_est_consigne(self, *_):
        t = Tache.objects.create(nom="trier")
        with mock.patch("apps.offres.services.pipeline.PipelineService.requalifier",
                        side_effect=RuntimeError("base injoignable")):
            with self.assertRaises(RuntimeError):
                call_command("trier", "--tache", str(t.pk), stdout=mock.MagicMock())
        t.refresh_from_db()
        self.assertEqual(t.statut, Tache.ECHEC)
        self.assertIn("base injoignable", t.detail)


@DOSSIER_TEMPORAIRE
class PageTaches(TestCase):

    def test_historique_et_journal(self):
        t = Tache.objects.create(nom="veille", statut=Tache.TERMINEE, detail="3 retenues")
        t.chemin_journal.parent.mkdir(exist_ok=True)
        t.chemin_journal.write_text("  → GET https://exemple.org\n  ← 200 en 0.10s\n")
        reponse = self.client.get("/taches/")
        self.assertContains(reponse, "3 retenues")
        self.assertContains(reponse, "← 200 en 0.10s")
        self.assertEqual(t.journal_recent.splitlines()[-1], "  ← 200 en 0.10s")

    def test_journal_absent(self):
        self.assertEqual(Tache(pk=10 ** 9, nom="trier").journal(), "")

    def test_cle_api_creee_affichee_une_fois_puis_revoquee(self):
        from apps.offres.auth import empreinte
        from apps.offres.models import CleApi
        reponse = self.client.post("/taches/cles/creer/", {"nom": "n8n"})
        cle = CleApi.objects.get(nom="n8n")
        jeton = reponse.context["jeton"]
        self.assertTrue(jeton.startswith("veille_"))
        self.assertEqual(cle.empreinte, empreinte(jeton))
        self.assertNotContains(self.client.get("/taches/"), jeton)
        self.assertIn("existe déjà", message(self.client.post("/taches/cles/creer/", {"nom": "n8n"})))
        self.client.post(f"/taches/cles/{cle.pk}/revoquer/")
        cle.refresh_from_db()
        self.assertFalse(cle.active)



class Planificateur(TestCase):

    def test_prochaine_execution(self):
        from datetime import datetime, time
        from apps.offres.management.commands.planifier import prochaine_execution
        six = time(6, 0)
        self.assertEqual(prochaine_execution(datetime(2026, 11, 13, 5, 59), six), datetime(2026, 11, 13, 6, 0))
        self.assertEqual(prochaine_execution(datetime(2026, 11, 13, 6, 0), six), datetime(2026, 11, 14, 6, 0))
        self.assertEqual(prochaine_execution(datetime(2026, 12, 31, 23, 0), six), datetime(2027, 1, 1, 6, 0))

    @DOSSIER_TEMPORAIRE
    def test_un_passage_lance_tout_en_automatique_et_attend(self):
        processus = mock.Mock(pid=os.getpid())
        processus.wait.return_value = 0
        with mock.patch("apps.offres.services.taches.subprocess.Popen", return_value=processus) as popen:
            call_command("planifier", "--une-fois", stdout=mock.MagicMock())
        tache = Tache.objects.get()
        self.assertEqual((tache.nom, tache.automatique), ("tout", True))
        self.assertEqual(popen.call_args.args[0][-3:], ["tout", "--tache", str(tache.pk)])
        processus.wait.assert_called_once()

    def test_un_passage_cede_a_une_tache_en_cours(self):
        Tache.objects.create(nom="trier", hote=socket.gethostname(), pid=os.getpid())
        with mock.patch("apps.offres.services.taches.subprocess.Popen") as popen:
            call_command("planifier", "--une-fois", stdout=mock.MagicMock())
        popen.assert_not_called()

    def test_heure_illisible(self):
        from django.core.management import CommandError
        with self.assertRaises(CommandError):
            call_command("planifier", "--une-fois", "--heure", "6h")


class Vivacite(TestCase):

    def test_un_pid_reattribue_n_est_pas_la_tache(self):
        from apps.offres.models import _processus_vivant, debut_processus
        moi = os.getpid()
        self.assertTrue(_processus_vivant(moi, debut_processus(moi)))
        self.assertFalse(_processus_vivant(moi, debut_processus(moi) + 1))


class OngletParametres(TestCase):

    @override_settings(VEILLE_HEURE="07:15")
    def test_heure_initiale_depuis_l_environnement(self):
        from datetime import time
        from apps.offres.models import Parametres
        self.assertEqual(Parametres.charger().heure_collecte, time(7, 15))
        self.assertContains(self.client.get("/parametres/"), 'value="07:15"')

    def test_enregistrer_une_heure(self):
        from datetime import time
        from apps.offres.models import Parametres
        reponse = self.client.post("/parametres/", {"heure_collecte": "05:30"}, HTTP_HX_REQUEST="true")
        self.assertEqual(Parametres.charger().heure_collecte, time(5, 30))
        self.assertEqual(message(reponse), "Collecte automatique réglée à 05:30.")
        self.assertContains(reponse, 'id="bloc-parametres"')

    def test_heure_illisible_refusee(self):
        from apps.offres.models import Parametres
        avant = Parametres.charger().heure_collecte
        reponse = self.client.post("/parametres/", {"heure_collecte": "25:99"}, HTTP_HX_REQUEST="true")
        self.assertIn("illisible", message(reponse))
        self.assertEqual(Parametres.charger().heure_collecte, avant)

    def test_planificateur_arrete_puis_actif(self):
        from django.utils import timezone
        from apps.offres.models import Parametres
        self.assertContains(self.client.get("/parametres/"), "Arrêté")
        Parametres.objects.filter(pk=Parametres.charger().pk).update(planificateur_vu_le=timezone.now())
        self.assertContains(self.client.get("/parametres/"), "Actif")


class BouclePlanificateur(TestCase):
    """Un tour par minute au plus ; l'heure reglee a l'ecran est relue a chaque tour."""

    def setUp(self):
        import io
        from datetime import time
        from zoneinfo import ZoneInfo
        from apps.offres.management.commands.planifier import Command
        from apps.offres.models import Parametres
        self.tz = ZoneInfo("Indian/Antananarivo")
        p = Parametres.charger()
        p.heure_collecte = time(6, 0)
        p.save()
        self.cmd = Command(stdout=io.StringIO())
        self.cmd.heure_imposee, self.cmd.cible, self.cmd.processus = None, None, []
        self.cmd.passage = mock.Mock()

    def a(self, h, m, s=0, jour=14):
        from datetime import datetime
        return datetime(2026, 11, jour, h, m, s, tzinfo=self.tz)

    def tour(self, *instants):
        with mock.patch("django.utils.timezone.localtime", side_effect=list(instants)):
            return self.cmd.tour()

    def test_attend_puis_lance_a_l_heure(self):
        from apps.offres.models import Parametres
        self.assertEqual(self.tour(self.a(5, 59, 30)), 30)
        self.cmd.passage.assert_not_called()
        self.assertIsNotNone(Parametres.charger().planificateur_vu_le)
        self.assertEqual(self.tour(self.a(6, 0), self.a(6, 0, 1)), 60)
        self.cmd.passage.assert_called_once()
        self.assertEqual(self.cmd.cible, self.a(6, 0, jour=15))

    def test_un_changement_d_heure_a_l_ecran_est_pris_en_compte(self):
        from datetime import time
        from apps.offres.models import Parametres
        self.tour(self.a(5, 0))
        self.assertEqual(self.cmd.cible, self.a(6, 0))
        Parametres.objects.update(heure_collecte=time(5, 30))
        self.tour(self.a(5, 1))
        self.assertEqual(self.cmd.cible, self.a(5, 30))
        self.cmd.passage.assert_not_called()



class ScraperB(FauxScraper):
    source_key = "b"
    nom = "B"
    vus = 0

    def scrape(self, seen_ids, complet=False):
        ScraperB.vus += 1
        return [item("b-1", "Construction d'un pont")]


@DOSSIER_TEMPORAIRE
class Reprise(TestCase):
    """Une tache coupee par un redemarrage reprend la ou elle s'etait arretee."""

    def interrompue(self, **champs):
        return Tache.objects.create(nom="tout", statut=Tache.INTERROMPUE,
                                    hote="ailleurs", **champs)

    @mock.patch("apps.offres.services.pipeline.enrichir_description", return_value="")
    @mock.patch("apps.offres.services.pipeline.REGISTRE_SCRAPERS", [FauxScraper, ScraperB])
    def test_la_collecte_saute_les_sources_deja_faites(self, _):
        from apps.offres.services.pipeline import PipelineService
        from apps.offres.services.taches import Progression
        FauxScraper.items, FauxScraper.recu, ScraperB.vus = [item("f-9", "Logiciel")], None, 0
        t = Tache.objects.create(nom="veille", reprise={"sources": ["faux"]})
        PipelineService.executer(notifier=False, progression=Progression(t.pk))
        self.assertIsNone(FauxScraper.recu, "la source deja faite ne doit pas etre rappelee")
        self.assertEqual(ScraperB.vus, 1)
        t.refresh_from_db()
        self.assertEqual(t.reprise["sources"], ["faux", "b"])

    def test_tout_reprend_a_la_phase_atteinte(self):
        t = Tache.objects.create(nom="tout", phase=3, reprise={"tri": 4})
        with mock.patch("apps.offres.services.pipeline.PipelineService.executer") as collecte, \
             mock.patch("apps.offres.services.pipeline.PipelineService.requalifier") as tri, \
             mock.patch("apps.offres.management.commands.tout.verifier_offres",
                        return_value=Counter()) as liens:
            call_command("tout", "--tache", str(t.pk), stdout=mock.MagicMock())
        collecte.assert_not_called()
        tri.assert_not_called()
        liens.assert_called_once()
        t.refresh_from_db()
        self.assertEqual(t.statut, Tache.TERMINEE)
        self.assertIn("4 verdict(s) modifié(s)", t.detail)

    def test_reprendre_relance_la_meme_tache_et_le_meme_journal(self):
        from apps.offres.services.taches import reprendre
        t = self.interrompue(etape="Collecte : BAD")
        t.chemin_journal.parent.mkdir(exist_ok=True)
        t.chemin_journal.write_text("debut du journal\n")
        with faux_popen() as popen:
            tache, _ = reprendre(t)
        self.assertEqual((tache.pk, tache.statut, tache.reprises), (t.pk, Tache.EN_COURS, 1))
        self.assertEqual(popen.call_args.args[0][-3:], ["tout", "--tache", str(t.pk)])
        journal = t.chemin_journal.read_text()
        self.assertTrue(journal.startswith("debut du journal"))
        self.assertIn("Reprise n°1", journal)

    def test_abandon_apres_trop_de_reprises(self):
        from apps.offres.services.taches import reprendre
        t = self.interrompue(reprises=Tache.REPRISES_MAX)
        with faux_popen() as popen:
            self.assertIsNone(reprendre(t))
        popen.assert_not_called()
        t.refresh_from_db()
        self.assertEqual(t.statut, Tache.ECHEC)

    def test_un_nouveau_lancement_remplace_l_interrompue(self):
        ancienne = self.interrompue()
        with faux_popen():
            self.client.post("/actions/lancer/tout/")
        ancienne.refresh_from_db()
        self.assertEqual(ancienne.statut, Tache.ANNULEE)

    def test_le_planificateur_reprend_au_tour_suivant(self):
        import io
        from apps.offres.management.commands.planifier import Command
        t = self.interrompue()
        cmd = Command(stdout=io.StringIO())
        cmd.heure_imposee, cmd.cible, cmd.processus = None, None, []
        with faux_popen():
            cmd.tour()
        t.refresh_from_db()
        self.assertEqual((t.statut, t.reprises), (Tache.EN_COURS, 1))
        self.assertEqual(len(cmd.processus), 1)

    def test_panneau_et_bouton_reprendre(self):
        t = self.interrompue(detail="Interrompue pendant « Collecte : BAD »")
        reponse = self.client.get("/actions/etat/")
        self.assertContains(reponse, f"/actions/tache/{t.pk}/reprendre/")
        self.assertContains(reponse, "every 5s")
        with faux_popen():
            reponse = self.client.post(f"/actions/tache/{t.pk}/reprendre/")
        self.assertEqual(message(reponse), "Traitement complet : reprise.")
        t.refresh_from_db()
        self.assertEqual(t.statut, Tache.EN_COURS)


class BattementDeCoeur(TestCase):

    def test_une_tache_d_un_autre_conteneur_vit_par_son_battement(self):
        from datetime import timedelta
        from django.utils import timezone
        t = Tache.objects.create(nom="veille", hote="veille-planificateur", pid=1)
        self.assertEqual(Tache.active(), t)
        Tache.objects.filter(pk=t.pk).update(maj_le=timezone.now() - timedelta(minutes=3))
        self.assertIsNone(Tache.active())
        t.refresh_from_db()
        self.assertEqual(t.statut, Tache.INTERROMPUE)

    def test_le_battement_rafraichit_la_tache(self):
        from datetime import timedelta
        from django.db import connection
        from django.utils import timezone
        from apps.offres.services.taches import _battre
        t = Tache.objects.create(nom="veille")
        Tache.objects.filter(pk=t.pk).update(maj_le=timezone.now() - timedelta(minutes=10))
        arret = mock.Mock()
        arret.wait.side_effect = [False, True]  # un battement, puis arret
        with mock.patch.object(connection, "close"):
            _battre(t.pk, arret)
        t.refresh_from_db()
        self.assertLess(timezone.now() - t.maj_le, timedelta(seconds=5))



@DOSSIER_TEMPORAIRE
class SuspendreAnnuler(TestCase):
    """Par tache et en global ; l'arret est cooperatif (battement de coeur)."""

    def en_cours(self, **champs):
        return Tache.objects.create(nom="tout", hote=socket.gethostname(), pid=os.getpid(),
                                    etape="Collecte : BAD", **champs)

    def test_suspendre_puis_reprendre_au_meme_point(self):
        t = self.en_cours(reprise={"sources": ["unjobnet"]}, reprises=Tache.REPRISES_MAX)
        reponse = self.client.post(f"/actions/tache/{t.pk}/suspendre/")
        t.refresh_from_db()
        self.assertEqual(t.statut, Tache.SUSPENDUE)
        self.assertIn("suspension", message(reponse))
        self.assertContains(reponse, f"/actions/tache/{t.pk}/reprendre/")
        # Une tache suspendue n'est pas reprise par le planificateur.
        self.assertIsNone(Tache.a_reprendre())
        # Reprise manuelle : meme apres la limite de reprises automatiques.
        with faux_popen():
            self.client.post(f"/actions/tache/{t.pk}/reprendre/")
        t.refresh_from_db()
        self.assertEqual((t.statut, t.reprise["sources"]), (Tache.EN_COURS, ["unjobnet"]))

    def test_annuler(self):
        t = self.en_cours()
        self.client.post(f"/actions/tache/{t.pk}/annuler/")
        t.refresh_from_db()
        self.assertEqual(t.statut, Tache.ANNULEE)
        self.assertIsNone(Tache.active())

    def test_action_impossible(self):
        t = Tache.objects.create(nom="trier", statut=Tache.TERMINEE)
        self.assertIn("Impossible", message(self.client.post(f"/actions/tache/{t.pk}/suspendre/")))
        self.assertEqual(self.client.get(f"/actions/tache/{t.pk}/annuler/").status_code, 405)

    def test_le_processus_s_arrete_de_lui_meme(self):
        from django.db import connection
        from apps.offres.services.taches import _battre
        t = self.en_cours(statut=Tache.SUSPENDUE)
        arret = mock.Mock()
        arret.wait.return_value = False
        arret.is_set.return_value = False
        with mock.patch("apps.offres.services.taches.os.kill") as tuer, \
                mock.patch.object(connection, "close"):
            _battre(t.pk, arret)
        tuer.assert_called_once_with(os.getpid(), __import__("signal").SIGTERM)

    def test_pas_d_arret_force_a_la_fin_normale(self):
        from django.db import connection
        from apps.offres.services.taches import _battre
        t = self.en_cours(statut=Tache.TERMINEE)
        arret = mock.Mock()
        arret.wait.return_value = False
        with mock.patch("apps.offres.services.taches.os.kill") as tuer, \
                mock.patch.object(connection, "close"):
            _battre(t.pk, arret)
        tuer.assert_not_called()

    def test_tout_suspendre_puis_tout_reprendre(self):
        from apps.offres.models import Parametres
        t = self.en_cours()
        i = Tache.objects.create(nom="liens", statut=Tache.INTERROMPUE)
        self.client.post("/actions/global/suspendre/")
        self.assertTrue(Parametres.charger().automatismes_suspendus)
        self.assertEqual(set(Tache.objects.values_list("statut", flat=True)), {Tache.SUSPENDUE})
        self.assertContains(self.client.get("/actions/etat/"), "Reprendre")
        with faux_popen() as popen:
            self.client.post("/actions/global/reprendre/")
        self.assertFalse(Parametres.charger().automatismes_suspendus)
        popen.assert_called_once()  # une seule a la fois
        t.refresh_from_db(); i.refresh_from_db()
        self.assertEqual((t.statut, i.statut), (Tache.EN_COURS, Tache.INTERROMPUE))

    def test_tout_annuler(self):
        self.en_cours()
        Tache.objects.create(nom="liens", statut=Tache.SUSPENDUE)
        Tache.objects.create(nom="trier", statut=Tache.TERMINEE)
        self.client.post("/actions/global/annuler/")
        self.assertEqual(sorted(Tache.objects.values_list("statut", flat=True)),
                         [Tache.ANNULEE, Tache.ANNULEE, Tache.TERMINEE])

    def test_automatismes_suspendus_signales_sur_chaque_page(self):
        from apps.offres.models import Parametres
        Parametres.objects.filter(pk=Parametres.charger().pk).update(automatismes_suspendus=True)
        self.assertContains(self.client.get("/actions/etat/"), "Automatismes suspendus")

    def test_le_planificateur_respecte_la_suspension(self):
        import io
        from apps.offres.management.commands.planifier import Command
        from apps.offres.models import Parametres
        Parametres.objects.filter(pk=Parametres.charger().pk).update(automatismes_suspendus=True)
        Tache.objects.create(nom="tout", statut=Tache.INTERROMPUE)
        cmd = Command(stdout=io.StringIO())
        cmd.heure_imposee, cmd.cible, cmd.processus = None, None, []
        with faux_popen() as popen:
            cmd.tour()
        popen.assert_not_called()


class EnTete(TestCase):

    def test_seul_tout_lancer_reste_dans_l_en_tete(self):
        page = self.client.get("/").content.decode()
        self.assertIn("/actions/lancer/tout/", page)
        for action in ("veille", "trier", "liens"):
            self.assertNotIn(f"/actions/lancer/{action}/", page)
        # Les actions separees restent sur la page Taches.
        self.assertIn("/actions/lancer/veille/", self.client.get("/taches/").content.decode())


class Parallele(TestCase):

    def test_resultats_rendus_dans_le_fil_appelant(self):
        import threading
        import time as t
        from apps.offres.services.parallele import en_parallele
        fils = set()

        def travail(cle, elements, emettre):
            for e in elements:
                t.sleep(0.05)
                emettre((e, threading.current_thread().name))

        debut = t.monotonic()
        recus = []
        for cle, (e, fil) in en_parallele({"a": [1, 2], "b": [3, 4], "c": [5, 6]}, travail, 3):
            recus.append(e)
            fils.add(fil)
            self.assertIs(threading.current_thread(), threading.main_thread())
        self.assertEqual(sorted(recus), [1, 2, 3, 4, 5, 6])
        self.assertEqual(fils, {"a", "b", "c"})
        self.assertLess(t.monotonic() - debut, 0.25, "les groupes doivent avancer en parallele")

    def test_une_erreur_remonte(self):
        from apps.offres.services.parallele import en_parallele

        def travail(cle, elements, emettre):
            raise RuntimeError("boum")

        with self.assertRaisesMessage(RuntimeError, "boum"):
            list(en_parallele({"a": [1]}, travail, 2))

    def test_sources_d_un_meme_domaine_groupees(self):
        from apps.offres.scrapers.banquemondiale import BanqueMondialeScraper
        from apps.offres.scrapers.bm_avis import BanqueMondialeAvisScraper
        self.assertEqual(BanqueMondialeAvisScraper.groupe, BanqueMondialeScraper.source_key)

    def test_une_session_http_par_fil(self):
        import threading
        from apps.offres.scrapers.http import session
        self.assertIs(session(), session())
        autre = []
        fil = threading.Thread(target=lambda: autre.append(session()))
        fil.start(); fil.join()
        self.assertIsNot(autre[0], session())


class LiensEnParallele(TestCase):

    @mock.patch("apps.offres.services.lien_checker.time.sleep")
    @mock.patch("apps.offres.services.lien_checker.verifier", return_value=("introuvable", "HTTP 404"))
    def test_chaque_lien_est_ecrit_et_les_delais_par_source(self, _verifier, dormir):
        from apps.offres.models import Offre
        from apps.offres.services.lien_checker import verifier_offres
        for i, source in enumerate(["bad", "bad", "fid", "banquemondiale", "banquemondiale-avis"]):
            Offre.objects.create(id=f"l-{i}", source=source, titre=f"Offre {i}", lien="https://x.org")
        offres = list(Offre.objects.values("id", "source", "titre", "lien"))
        verdicts = verifier_offres(offres, ecrire=lambda *_: None)
        self.assertEqual(verdicts["introuvable"], 5)
        self.assertEqual(Offre.objects.filter(lien_etat="introuvable").count(), 5)
        # Une pause entre deux liens d'un meme domaine (bad x2, banque mondiale x2), pas ailleurs.
        self.assertEqual(dormir.call_count, 2)
