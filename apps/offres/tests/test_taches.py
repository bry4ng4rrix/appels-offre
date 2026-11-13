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
        self.assertContains(reponse, 'hx-trigger="every 1s"')
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
        self.assertEqual(Tache.objects.get().statut, Tache.ECHEC)


class Etat(TestCase):

    def test_rien_en_cours(self):
        self.assertEqual(self.client.get("/actions/etat/").content, b"")

    def test_en_cours(self):
        Tache.objects.create(nom="veille", hote=socket.gethostname(), pid=os.getpid(),
                             etape="Collecte : BAD", courant=5, total=22)
        reponse = self.client.get("/actions/etat/")
        self.assertContains(reponse, "Collecte : BAD")
        self.assertContains(reponse, "5 / 22 · 22 %")
        self.assertContains(reponse, "every 1s")

    def test_la_fin_est_annoncee_une_fois_au_panneau_qui_suivait(self):
        t = Tache.objects.create(nom="trier", statut=Tache.TERMINEE, detail="12 verdicts modifiés")
        reponse = self.client.get(f"/actions/etat/?suivi={t.pk}")
        self.assertContains(reponse, "12 verdicts modifiés")
        self.assertNotContains(reponse, "every 1s")
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
        self.cmd.heure_imposee, self.cmd.cible = None, None
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
