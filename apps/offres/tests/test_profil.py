"""Profil (sections A à E, CV), suggestions avec score, alertes email."""

import io
import shutil
import tempfile
import zipfile
from collections import Counter
from datetime import timedelta
from unittest import mock

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.offres.models import (Categorie, Competence, Notification, Offre, Parametres, Pays,
                                Preferences, Profil, Secteur, Tache)
from apps.offres.services import alertes
from apps.offres.services.correspondance import criteres, score, suggestions
from apps.offres.tests.outils import connecter

User = get_user_model()
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def docx() -> bytes:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        archive.writestr("word/document.xml", "<w:document/>")
    return tampon.getvalue()


def membre(email="membre@exemple.org", verifie=True):
    user = User.objects.create_user(email.split("@")[0], email=email, password="mdp-de-test-1234")
    EmailAddress.objects.create(user=user, email=email, verified=verifie, primary=True)
    return user


class AvecFichiers(TestCase):
    """MEDIA_ROOT jetable : les tests n'ecrivent pas dans le vrai dossier prive."""

    def setUp(self):
        super().setUp()
        self.dossier = tempfile.mkdtemp()
        reglage = override_settings(MEDIA_ROOT=self.dossier)
        reglage.enable()
        self.addCleanup(reglage.disable)
        self.addCleanup(shutil.rmtree, self.dossier, ignore_errors=True)


class Completion(AvecFichiers):

    def setUp(self):
        super().setUp()
        self.user = connecter(self.client, admin=False)
        self.madagascar = Pays.objects.create(code="madagascar", nom="Madagascar")

    def poster(self, section, suivant="", fichiers=None, **champs):
        donnees = {f"{section}-{k}": v for k, v in champs.items()}
        donnees.update({"section": section, "suivant": suivant}, **(fichiers or {}))
        return self.client.post("/profil/", donnees)

    def test_l_inscription_mene_a_la_completion_du_profil(self):
        self.client.logout()
        reponse = self.client.post("/comptes/signup/", {
            "email": "neuf@exemple.org", "password1": "Un-mot-de-passe-42", "password2": "Un-mot-de-passe-42"})
        self.assertEqual(reponse["Location"], "/profil/?bienvenue=1")
        self.assertContains(self.client.get(reponse["Location"]), "Bienvenue")

    def test_informations_personnelles(self):
        reponse = self.poster("perso", suivant="pro", first_name="Jean", last_name="Rakoto",
                              telephone="+261 34 00 000 00", ville="Antananarivo",
                              pays=self.madagascar.pk, adresse="Lot II", code_postal="101")
        self.assertEqual(reponse["Location"], "/profil/#pro")
        self.user.refresh_from_db()
        fiche = Profil.de(self.user)
        self.assertEqual((self.user.first_name, fiche.telephone, fiche.pays), ("Jean", "+261 34 00 000 00", self.madagascar))
        self.assertGreater(fiche.completion(), 0)

    def test_saisie_invalide_rouvre_la_section_sans_rien_perdre(self):
        reponse = self.poster("perso", telephone="appelez-moi", first_name="Jean")
        self.assertEqual(reponse.status_code, 400)
        self.assertContains(reponse, 'data-onglet-actif="perso"', status_code=400)
        self.assertContains(reponse, 'value="Jean"', status_code=400)
        self.assertEqual(Profil.de(self.user).telephone, "")

    def test_domaines_et_competences_sans_doublon(self):
        Secteur.objects.get_or_create(code="informatique", defaults={"nom": "Informatique"})[0]
        web = Categorie.objects.get(code="developpement-web")
        self.poster("domaines", secteurs=[Secteur.objects.get(code="informatique").pk],
                    categories=[web.pk], competences_texte="Python, django ; PYTHON",
                    mots_cles="ONG, ong, SIG")
        fiche = Profil.de(self.user)
        self.assertEqual(sorted(fiche.competences.values_list("nom", flat=True)), ["Python", "django"])
        self.assertEqual(fiche.mots_cles, "ONG, SIG")
        # Un autre utilisateur reutilise la meme competence, quelle que soit la casse.
        autre = membre("autre@exemple.org")
        Profil.de(autre)
        self.client.force_login(autre)
        self.poster("domaines", competences_texte="python")
        self.assertEqual(Competence.objects.filter(nom__iexact="python").count(), 1)

    def test_preferences(self):
        self.poster("preferences", suivant="suggestions", regions=["afrique"], pays=[self.madagascar.pk],
                    types_offres=["emploi"], villes="Tamatave, tamatave", seuil="60", notifications="on")
        prefs = Preferences.de(self.user)
        self.assertEqual((prefs.regions, prefs.types_offres, prefs.villes, prefs.seuil),
                         (["afrique"], ["emploi"], "Tamatave", 60))
        self.assertTrue(prefs.notifications)

    def test_cv_importer_telecharger_remplacer_supprimer(self):
        self.poster("cv", fichiers={"cv-fichier": SimpleUploadedFile("Mon CV.pdf", PDF)})
        fiche = Profil.de(self.user)
        self.assertEqual(fiche.cv_nom, "Mon CV.pdf")
        self.assertNotIn("Mon CV", fiche.cv.name)  # nom aleatoire sur disque
        reponse = self.client.get(f"/profil/cv/{self.user.pk}/")
        self.assertIn('filename="Mon CV.pdf"', reponse["Content-Disposition"])
        self.assertEqual(b"".join(reponse.streaming_content), PDF)

        ancien = fiche.cv.path
        self.poster("cv", fichiers={"cv-fichier": SimpleUploadedFile("cv.docx", docx())})
        self.assertFalse(shutil.os.path.exists(ancien))
        self.assertEqual(Profil.de(self.user).cv_nom, "cv.docx")

        chemin = Profil.de(self.user).cv.path
        self.client.post("/profil/", {"section": "cv-supprimer"})
        self.assertFalse(Profil.de(self.user).cv)
        self.assertFalse(shutil.os.path.exists(chemin))

    def test_cv_controle_format_et_taille(self):
        for nom, contenu in (("faux.pdf", b"bonjour"), ("cv.exe", PDF), ("faux.docx", b"PK pas un zip"),
                             ("gros.pdf", PDF + b"0" * (5 * 1024 * 1024))):
            with self.subTest(nom=nom):
                reponse = self.poster("cv", fichiers={"cv-fichier": SimpleUploadedFile(nom, contenu)})
                self.assertEqual(reponse.status_code, 400)
        self.assertFalse(Profil.de(self.user).cv)

    def test_cv_et_photo_invisibles_pour_un_autre_user(self):
        self.poster("cv", fichiers={"cv-fichier": SimpleUploadedFile("cv.pdf", PDF)})
        self.poster("perso", fichiers={"perso-photo": SimpleUploadedFile("moi.png", PNG)})
        proprietaire = self.user.pk
        self.assertEqual(self.client.get(f"/profil/photo/{proprietaire}/")["Content-Type"], "image/png")
        self.client.force_login(membre("curieux@exemple.org"))
        for url in (f"/profil/cv/{proprietaire}/", f"/profil/photo/{proprietaire}/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(connecter(self.client))  # admin
        self.assertEqual(self.client.get(f"/profil/cv/{proprietaire}/").status_code, 200)

    def test_photo_qui_n_est_pas_une_image_refusee(self):
        reponse = self.poster("perso", fichiers={"perso-photo": SimpleUploadedFile("moi.png", b"<svg/>")})
        self.assertEqual(reponse.status_code, 400)
        self.assertFalse(Profil.de(self.user).photo)


class Correspondance(TestCase):

    def setUp(self):
        self.user = membre()
        self.mada = Pays.objects.create(code="madagascar", nom="Madagascar")
        self.info = Secteur.objects.get_or_create(code="informatique", defaults={"nom": "Informatique"})[0]
        fiche = Profil.de(self.user)
        fiche.pays = self.mada
        fiche.save()
        fiche.secteurs.add(self.info)
        fiche.competences.add(Competence.objects.create(nom="Python"))
        self.demain = timezone.now().date() + timedelta(days=10)

    def offre(self, id, **champs):
        return Offre.objects.create(**({"id": id, "source": "test", "titre": id, "pays": "Madagascar",
                                        "secteur": "informatique", "date_limite": self.demain} | champs))

    def test_filtre_par_defaut_pays_et_region_de_residence(self):
        c = criteres(self.user)
        self.assertEqual((c.pays, c.regions), ({"madagascar"}, {"madagascar"}))

    def test_score(self):
        c = criteres(self.user)
        self.assertEqual(score(self.offre("a", titre="Développeur Python senior"), c), 100)
        # Ni la competence (java != javascript), ni le lieu, ni le secteur.
        self.assertEqual(score(self.offre("b", titre="Dev JavaScript", pays="Kenya", secteur="sante"), c), 0)
        # Lieu et secteur sans la competence : 40 points sur 80 possibles.
        self.assertEqual(score(self.offre("c", titre="Chef de projet"), c), round(100 * 40 / 80))

    def test_la_ponderation_se_regle(self):
        Parametres.objects.update_or_create(pk=1, defaults={"poids": {"competences": 0}})
        self.assertEqual(score(self.offre("c", titre="Chef de projet"), criteres(self.user)), 100)

    def test_suggestions_triees_et_offres_closes_exclues(self):
        self.offre("parfaite", titre="Python Django")
        self.offre("moyenne", titre="Chef de projet")
        self.offre("close", titre="Python", date_limite=timezone.now().date() - timedelta(days=1))
        self.offre("ailleurs", titre="Peinture", pays="Kenya", secteur="construction")
        _, offres = suggestions(self.user)
        self.assertEqual([o.id for o in offres], ["parfaite", "moyenne"])

    def test_page_pour_vous(self):
        self.offre("parfaite", titre="Python Django")
        self.client.force_login(self.user)
        reponse = self.client.get("/pour-vous/")
        self.assertContains(reponse, "parfaite")
        self.assertContains(reponse, "100 %")
        self.assertContains(reponse, "Madagascar (pays de résidence)")

    def test_profil_vide_invite_a_le_completer(self):
        self.client.force_login(membre("vide@exemple.org"))
        self.assertContains(self.client.get("/pour-vous/"), "Compléter mon profil")


class Alertes(TestCase):

    def setUp(self):
        self.user = membre()
        fiche = Profil.de(self.user)
        fiche.secteurs.add(Secteur.objects.get_or_create(code="informatique", defaults={"nom": "Informatique"})[0])
        fiche.competences.add(Competence.objects.create(nom="Python"))
        Preferences.de(self.user)
        # Repere : seules les offres creees apres comptent.
        Parametres.objects.update_or_create(pk=1, defaults={"alertes_depuis": timezone.now() - timedelta(seconds=1)})

    def offre(self, id, **champs):
        return Offre.objects.create(**({"id": id, "source": "test", "titre": f"Developpeur Python {id}",
                                        "secteur": "informatique", "lien": "https://exemple.org"} | champs))

    def test_une_nouvelle_offre_pertinente_part_une_seule_fois(self):
        self.offre("o1")
        self.assertEqual(alertes.traiter()["emails"], 1)
        self.assertEqual(mail.outbox[0].to, ["membre@exemple.org"])
        self.assertIn("Developpeur Python o1", mail.outbox[0].body)
        n = Notification.objects.get()
        self.assertEqual((n.statut, n.score, n.tentatives), (Notification.ENVOYEE, 100, 1))
        # Second passage, meme offre (repere remis en arriere) : aucun doublon.
        Parametres.objects.update(alertes_depuis=timezone.now() - timedelta(days=1))
        self.assertEqual(alertes.traiter()["emails"], 0)
        self.assertEqual((len(mail.outbox), Notification.objects.count()), (1, 1))

    def test_ni_adresse_non_verifiee_ni_alertes_coupees_ni_sous_le_seuil(self):
        EmailAddress.objects.filter(user=self.user).update(verified=False)
        self.offre("o1")
        alertes.traiter()
        EmailAddress.objects.filter(user=self.user).update(verified=True)
        Preferences.objects.filter(user=self.user).update(notifications=False)
        self.offre("o2")
        alertes.traiter()
        Preferences.objects.filter(user=self.user).update(notifications=True, seuil=100)
        self.offre("o3", titre="Chef de projet")  # secteur seul : 25/65
        alertes.traiter()
        self.assertEqual(len(mail.outbox), 0)

    def test_echec_d_envoi_retente_au_passage_suivant(self):
        self.offre("o1")
        with mock.patch("apps.offres.services.notification.NotificationService.envoyer_a",
                        side_effect=OSError("SMTP injoignable")):
            self.assertEqual(alertes.traiter()["echecs"], 1)
        n = Notification.objects.get()
        self.assertEqual((n.statut, n.tentatives, n.erreur), (Notification.ECHEC, 1, "SMTP injoignable"))
        self.assertEqual(alertes.envoyer()["emails"], 1)
        n.refresh_from_db()
        self.assertEqual((n.statut, n.erreur), (Notification.ENVOYEE, ""))

    def test_au_dela_des_tentatives_on_abandonne(self):
        Notification.objects.create(user=self.user, offre=self.offre("o1"), score=90,
                                    statut=Notification.ECHEC, tentatives=Notification.TENTATIVES_MAX)
        Parametres.objects.update(alertes_depuis=timezone.now())
        self.assertEqual(alertes.envoyer()["emails"], 0)

    @override_settings(API_PUBLIQUE_SOURCES_EXCLUES=["unjobnet"])
    def test_les_sources_non_rediffusables_ne_partent_pas(self):
        self.offre("o1", source="unjobnet")
        alertes.traiter()
        self.assertFalse(Notification.objects.exists())

    def test_le_traitement_complet_envoie_les_alertes_a_la_fin(self):
        t = Tache.objects.create(nom="tout", phase=3)
        with mock.patch("apps.offres.management.commands.tout.verifier_offres", return_value=Counter()), \
             mock.patch("apps.offres.services.alertes.traiter",
                        return_value={"creees": 1, "emails": 1, "offres": 1, "echecs": 0}) as traiter:
            call_command("tout", "--tache", str(t.pk), stdout=mock.MagicMock())
        traiter.assert_called_once()

    def test_des_alertes_en_panne_ne_font_pas_echouer_le_passage(self):
        t = Tache.objects.create(nom="tout", phase=3)
        with mock.patch("apps.offres.management.commands.tout.verifier_offres", return_value=Counter()), \
             mock.patch("apps.offres.services.alertes.traiter", side_effect=RuntimeError("panne")):
            call_command("tout", "--tache", str(t.pk), stdout=mock.MagicMock(), stderr=mock.MagicMock())
        t.refresh_from_db()
        self.assertEqual(t.statut, Tache.TERMINEE)

    def test_historique_visible_par_son_seul_proprietaire(self):
        self.offre("o1")
        alertes.traiter()
        self.client.force_login(self.user)
        self.assertContains(self.client.get("/notifications/"), "Developpeur Python o1")
        self.client.force_login(membre("autre@exemple.org"))
        self.assertNotContains(self.client.get("/notifications/"), "Developpeur Python o1")


class GuidePasAPas(TestCase):
    """Après l'inscription, une bulle d'aide par bouton, une fois par page."""

    def setUp(self):
        self.user = membre()
        self.client.force_login(self.user)

    def test_le_guide_demarre_a_la_premiere_visite_seulement(self):
        page = self.client.get("/profil/")
        self.assertContains(page, 'data-guide-page="web-profil" data-guide-auto')
        self.assertContains(page, 'data-aide-titre="Votre CV"')
        self.assertEqual(self.client.post("/guide/vu/", {"page": "web-profil"}).status_code, 204)
        self.client.post("/guide/vu/", {"page": "web-profil"})
        self.assertEqual(Profil.de(self.user).guides_vus, ["web-profil"])
        self.assertNotContains(self.client.get("/profil/"), "data-guide-auto")
        # Les autres pages gardent leur premiere visite guidee.
        self.assertContains(self.client.get("/pour-vous/"), "data-guide-auto")

    def test_page_inconnue_refusee(self):
        self.assertEqual(self.client.post("/guide/vu/", {"page": "../admin"}).status_code, 400)
        self.assertEqual(Profil.de(self.user).guides_vus, [])

    def test_pas_de_demarrage_seul_pour_un_admin_ni_pour_un_visiteur(self):
        self.client.force_login(connecter(self.client))
        self.assertNotContains(self.client.get("/offres/"), "data-guide-auto")
        self.client.logout()
        self.assertNotContains(self.client.get("/comptes/login/"), "data-guide-auto")
        self.assertNotContains(self.client.get("/comptes/login/"), "guide.js")
