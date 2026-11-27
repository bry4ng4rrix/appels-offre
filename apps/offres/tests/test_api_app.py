"""API applicative /api/v1/ (DRF) : connexion allauth headless (X-Session-Token), cookie + CSRF,
debit, credits, profil, abonnements, routes d'administration et contrat OpenAPI."""

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from rest_framework.throttling import UserRateThrottle

from apps.offres.models import (Abonnement, CleApi, Consultation, Inscription, Offre, Parametres, Plan,
                                Profil, Secteur, Suivi, Tache)

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
MDP = "mdp-de-test-1234"


def offres(n):
    return [Offre.objects.create(id=f"a-{i}", source="test", titre=f"Offre {i}", pertinent=True,
                                 lien=f"https://exemple.org/{i}") for i in range(n)]


class Api(TestCase):
    """Un client qui parle JSON avec le jeton de session des applis."""

    jeton = ""

    def appel(self, methode, url, corps=None, **extra):
        if self.jeton:
            extra["HTTP_X_SESSION_TOKEN"] = self.jeton
        if corps is not None:
            extra.update(data=json.dumps(corps), content_type="application/json")
        return getattr(self.client, methode)(url, **extra)

    def connecter_appli(self, email, admin=False):
        get_user_model().objects.create_user(email, email=email, password=MDP, is_staff=admin)
        reponse = self.client.post("/_allauth/app/v1/auth/login", json.dumps(
            {"email": email, "password": MDP}), content_type="application/json")
        self.assertEqual(reponse.status_code, 200, reponse.content)
        self.jeton = reponse.json()["meta"]["session_token"]


class Connexion(Api):

    def test_inscription_connexion_et_deconnexion_par_jeton(self):
        reponse = self.client.post("/_allauth/app/v1/auth/signup", json.dumps(
            {"email": "nouveau@exemple.org", "password": MDP}), content_type="application/json")
        self.assertEqual(reponse.status_code, 200, reponse.content)
        self.jeton = reponse.json()["meta"]["session_token"]
        moi = self.appel("get", "/api/v1/moi/").json()
        self.assertEqual((moi["email"], moi["admin"]), ("nouveau@exemple.org", False))
        essai = (timezone.localdate() + timedelta(days=13)).isoformat()  # 14 jours, aujourd'hui compris
        self.assertEqual((moi["credits"]["illimites"], moi["credits"]["essai_jusqu_au"]), (True, essai))
        self.appel("delete", "/_allauth/app/v1/auth/session")
        self.assertEqual(self.appel("get", "/api/v1/moi/").status_code, 401)

    def test_sans_jeton_ou_jeton_faux_401_en_json(self):
        refus = self.client.get("/api/v1/moi/")
        self.assertEqual(refus.status_code, 401)
        self.assertEqual(refus["WWW-Authenticate"], "X-Session-Token")
        self.assertIn("erreur", refus.json())
        self.jeton = "faux"
        self.assertEqual(self.appel("get", "/api/v1/offres/").status_code, 401)

    def test_toute_route_non_publique_exige_une_connexion(self):
        """Une nouvelle route /api/v1/ ne peut pas s'ouvrir sans connexion sans que ce test le voie."""
        from apps.offres.urls import urlpatterns
        publiques = {"api/v1/reference/", "api/v1/plans/"}
        routes = [str(p.pattern) for p in urlpatterns
                  if str(p.pattern).startswith("api/v1/") and str(p.pattern) not in publiques]
        self.assertGreater(len(routes), 40)
        for route in routes:
            url = "/" + re.sub(r"<[^>]+>", "1", route.replace("<catalogue:catalogue>", "secteurs"))
            for methode in ("get", "post"):
                with self.subTest(url=url, methode=methode):
                    self.assertEqual(getattr(self.client, methode)(url).status_code, 401)

    def test_une_session_d_appli_n_ouvre_pas_l_api_machine(self):
        self.connecter_appli("chef@exemple.org", admin=True)
        self.assertEqual(self.appel("get", "/api/statistiques/").status_code, 401)
        self.assertEqual(self.appel("get", "/api/v1/admin/statistiques/").status_code, 200)

    def test_routes_publiques(self):
        self.assertEqual(self.client.get("/api/v1/reference/").status_code, 200)
        self.assertEqual(len(self.client.get("/api/v1/plans/").json()), 3)

    def test_cookie_de_session_exige_le_csrf_pour_ecrire(self):
        navigateur = Client(enforce_csrf_checks=True)
        user = get_user_model().objects.create_user("n", email="n@exemple.org")
        navigateur.force_login(user)
        self.assertEqual(navigateur.get("/api/v1/moi/").status_code, 200)
        plan = Plan.objects.get(nom="Standard")
        refus = navigateur.post("/api/v1/abonnements/", json.dumps({"plan": plan.pk}),
                                content_type="application/json")
        self.assertEqual(refus.status_code, 403)
        self.assertFalse(Abonnement.objects.exists())


class Contrat(Api):

    def test_schema_openapi_reserve_aux_admins_hors_debug(self):
        self.assertEqual(self.client.get("/api/v1/schema/").status_code, 401)
        self.connecter_appli("chef@exemple.org", admin=True)
        schema = self.appel("get", "/api/v1/schema/", HTTP_ACCEPT="application/json")
        self.assertEqual(schema.status_code, 200)
        contrat = schema.json()
        self.assertIn("/api/v1/offres/{offre_id}/consulter/", contrat["paths"])
        self.assertEqual(contrat["components"]["securitySchemes"]["jetonSession"]["name"], "X-Session-Token")

    def test_l_api_publique_ne_donne_plus_le_lien_officiel(self):
        offres(1)
        with override_settings(API_PUBLIQUE_SOURCES_EXCLUES=[]):
            corps = self.client.get("/api/public/offres/?cloturees=1").content.decode()
        self.assertIn("Offre 0", corps)
        self.assertNotIn("exemple.org/0", corps)

    def test_export_et_recapitulatif_reserves_aux_admins(self):
        get_user_model().objects.create_user("m", email="m@exemple.org", password=MDP)
        self.client.login(username="m", password=MDP)
        self.assertEqual(self.client.get("/exporter/").status_code, 403)
        self.assertEqual(self.client.get("/recapitulatif/").status_code, 403)


class Offres(Api):

    def test_le_lien_officiel_coute_un_credit_et_n_est_pas_dans_la_liste(self):
        self.connecter_appli("membre@exemple.org")
        # Sans essai : un lot de 10 credits.
        Abonnement.objects.create(user=get_user_model().objects.get(email="membre@exemple.org"),
                                  plan=Plan.objects.get(nom="Standard"), statut=Abonnement.VALIDE,
                                  debut=timezone.localdate(), credits_restants=10)
        lot = offres(11)
        liste = self.appel("get", "/api/v1/offres/?par_page=5").json()
        self.assertEqual((liste["total"], len(liste["resultats"]), liste["pages"]), (11, 5, 3))
        self.assertNotIn("lien", liste["resultats"][0])
        for o in lot[:-1]:
            self.assertEqual(self.appel("post", f"/api/v1/offres/{o.pk}/consulter/").json()["lien"], o.lien)
        epuise = self.appel("post", f"/api/v1/offres/{lot[-1].pk}/consulter/")
        self.assertEqual((epuise.status_code, epuise.json()["code"]), (402, "credits_epuises"))
        fiche = self.appel("get", f"/api/v1/offres/{lot[0].pk}/").json()
        self.assertTrue(fiche["deja_consultee"])
        self.assertNotIn("suivi", fiche)
        self.assertNotIn("lien", fiche)

    def test_ouvrir_en_rafale_est_freine(self):
        self.connecter_appli("membre@exemple.org")
        Inscription.objects.create(user=get_user_model().objects.get(email="membre@exemple.org"),
                                   essai_jusqu_au=timezone.localdate())
        o = offres(1)[0]
        with mock.patch.dict(UserRateThrottle.THROTTLE_RATES, {"consulter": "2/min"}):
            codes = [self.appel("post", f"/api/v1/offres/{o.pk}/consulter/").status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])

    def test_l_admin_voit_le_lien_et_decide(self):
        self.connecter_appli("chef@exemple.org", admin=True)
        o = offres(1)[0]
        self.assertEqual(self.appel("get", "/api/v1/offres/").json()["resultats"][0]["lien"], o.lien)
        reponse = self.appel("post", f"/api/v1/admin/offres/{o.pk}/decision/", {"statut": "candidature"})
        self.assertEqual(reponse.status_code, 201)
        self.assertEqual(Suivi.objects.get().decide_par.email, "chef@exemple.org")
        self.assertIn("statut", self.appel("post", f"/api/v1/admin/offres/{o.pk}/decision/",
                                           {"statut": "inconnu"}).json()["champs"])
        echeance = self.appel("post", f"/api/v1/admin/offres/{o.pk}/echeance/", {"echeance": "2027-01-15"})
        self.assertEqual(echeance.json()["echeance"], "2027-01-15")
        self.assertEqual(str(Offre.objects.get().date_limite), "2027-01-15")
        self.assertEqual(self.appel("get", "/api/v1/admin/suivi/").json()["total"], 1)

    def test_un_membre_ne_peut_pas_decider(self):
        self.connecter_appli("membre@exemple.org")
        o = offres(1)[0]
        self.assertEqual(self.appel("post", f"/api/v1/admin/offres/{o.pk}/verdict/",
                                    {"pertinent": False}).status_code, 403)
        self.assertEqual(self.appel("get", "/api/v1/admin/exporter/").status_code, 403)
        self.assertTrue(Offre.objects.get().pertinent)


class ProfilEtAbonnement(Api):

    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        reglage = override_settings(MEDIA_ROOT=self.dossier)
        reglage.enable()
        self.addCleanup(reglage.disable)
        self.addCleanup(shutil.rmtree, self.dossier, ignore_errors=True)
        self.connecter_appli("membre@exemple.org")

    def test_sections_du_profil_et_erreurs_par_champ(self):
        eau = Secteur.objects.create(code="eau-test", nom="Eau test")
        profil = self.appel("put", "/api/v1/profil/domaines/", {
            "secteurs": [eau.pk], "categories": [], "competences_texte": "Python, SIG",
            "mots_cles": "ONG"}).json()
        self.assertEqual(profil["domaines"]["secteurs"], [eau.pk])
        self.assertEqual(profil["domaines"]["competences_texte"], "Python, SIG")
        invalide = self.appel("put", "/api/v1/profil/pro/", {"annees_experience": "beaucoup"})
        self.assertEqual(invalide.status_code, 400)
        self.assertIn("annees_experience", invalide.json()["champs"])
        # La regle du formulaire du site s'applique aussi : 30 competences au plus.
        trop = self.appel("put", "/api/v1/profil/domaines/", {
            "competences_texte": ", ".join(f"c{i}" for i in range(31))})
        self.assertIn("competences_texte", trop.json()["champs"])
        self.assertEqual(self.appel("get", "/api/v1/profil/").json()["domaines"]["mots_cles"], "ONG")

    def test_cv_depot_lecture_suppression(self):
        depot = self.client.post("/api/v1/profil/cv/", {"fichier": SimpleUploadedFile("Mon CV.pdf", PDF)},
                                 HTTP_X_SESSION_TOKEN=self.jeton)
        self.assertEqual(depot.status_code, 201, depot.content)
        lecture = self.appel("get", "/api/v1/profil/cv/", HTTP_ACCEPT="application/pdf")
        self.assertEqual(b"".join(lecture.streaming_content), PDF)
        self.assertEqual(self.appel("delete", "/api/v1/profil/cv/").status_code, 204)
        self.assertFalse(Profil.objects.get().cv)
        refus = self.client.post("/api/v1/profil/cv/", {"fichier": SimpleUploadedFile("cv.pdf", b"pas un pdf")},
                                 HTTP_X_SESSION_TOKEN=self.jeton)
        self.assertEqual(refus.status_code, 400)

    def test_demande_puis_validation_par_l_admin(self):
        mensuel = Plan.objects.get(nom="Mensuel")
        demande = self.appel("post", "/api/v1/abonnements/", {"plan": mensuel.pk})
        self.assertEqual(demande.status_code, 201)
        self.assertEqual(self.appel("post", "/api/v1/abonnements/", {"plan": mensuel.pk}).status_code, 409)
        membre = self.jeton
        self.connecter_appli("chef@exemple.org", admin=True)
        liste = self.appel("get", "/api/v1/admin/abonnements/?statut=attente").json()
        self.assertEqual(liste["en_attente"], 1)
        pk = liste["resultats"][0]["id"]
        self.assertEqual(self.appel("post", f"/api/v1/admin/abonnements/{pk}/valider/").json()["etat"], "actif")
        self.assertEqual(self.appel("post", f"/api/v1/admin/abonnements/{pk}/refuser/").status_code, 404)
        self.jeton = membre
        self.assertEqual(self.appel("get", "/api/v1/abonnements/").json()["credits"]["du_jour"],
                         50)


class Administration(Api):

    def setUp(self):
        self.connecter_appli("chef@exemple.org", admin=True)

    def test_reserve_aux_admins(self):
        self.connecter_appli("membre@exemple.org")
        for url in ("/api/v1/admin/taches/", "/api/v1/admin/parametres/", "/api/v1/admin/cles/"):
            self.assertEqual(self.appel("get", url).status_code, 403, url)

    def test_parametres_et_ponderation(self):
        self.assertEqual(self.appel("post", "/api/v1/admin/parametres/collecte/",
                                    {"intervalle_collecte": 30}).status_code, 400)
        ok = self.appel("post", "/api/v1/admin/parametres/collecte/",
                        {"intervalle_collecte": 3, "heure_nuit": "01:30", "pause_weekend": False})
        self.assertEqual(ok.status_code, 200)
        reglages = Parametres.charger()
        self.assertEqual((reglages.intervalle_collecte, f"{reglages.heure_nuit:%H:%M}", reglages.pause_weekend),
                         (3, "01:30", False))
        poids = {"competences": 50, "domaine": 20, "categorie": 10, "localisation": 10, "mots_cles": 10}
        self.assertEqual(self.appel("post", "/api/v1/admin/parametres/pertinence/", poids).status_code, 200)
        self.assertEqual(Parametres.charger().poids, poids)
        email = self.appel("post", "/api/v1/admin/parametres/email/",
                           {"smtp_hote": "smtp.exemple.org", "destinataires": ["a@exemple.org", "pas-un-email"]})
        self.assertEqual(email.status_code, 400)
        self.assertIn("pas-un-email", email.json()["erreur"])
        lecture = self.appel("get", "/api/v1/admin/parametres/").json()
        self.assertEqual(lecture["collecte"]["intervalle_collecte"], 3)
        self.assertFalse(lecture["collecte"]["pause_weekend"])
        self.assertNotIn("smtp_mot_de_passe", lecture["email"])

    def test_catalogue_des_secteurs(self):
        cree = self.appel("post", "/api/v1/admin/secteurs/", {"nom": "Énergie solaire"})
        self.assertEqual(cree.status_code, 201)
        secteur = Secteur.objects.get(nom="Énergie solaire")
        self.assertEqual(self.appel("post", "/api/v1/admin/secteurs/", {"nom": "Énergie solaire"}).status_code, 400)
        self.appel("patch", f"/api/v1/admin/secteurs/{secteur.pk}/", {"nom": "Solaire"})
        self.appel("post", f"/api/v1/admin/secteurs/{secteur.pk}/basculer/")
        secteur.refresh_from_db()
        self.assertEqual((secteur.nom, secteur.actif), ("Solaire", False))
        self.assertIn("Solaire", [x["nom"] for x in self.appel("get", "/api/v1/admin/secteurs/").json()])
        self.assertEqual(self.appel("get", "/api/v1/admin/inconnu/").status_code, 404)

    def test_cle_machine_creee_par_l_api_ouvre_l_api_machine(self):
        jeton = self.appel("post", "/api/v1/admin/cles/", {"nom": "n8n"}).json()["jeton"]
        self.assertEqual(self.client.get("/api/statistiques/", HTTP_AUTHORIZATION=f"Bearer {jeton}").status_code, 200)
        cle = CleApi.objects.get()
        self.appel("delete", f"/api/v1/admin/cles/{cle.pk}/")
        self.assertEqual(self.client.get("/api/statistiques/", HTTP_AUTHORIZATION=f"Bearer {jeton}").status_code, 401)

    def test_plans(self):
        cree = self.appel("post", "/api/v1/admin/plans/", {"nom": "Annuel", "prix": 500000, "credits": 100,
                                                           "par_jour": True, "duree_jours": 365})
        self.assertEqual(cree.status_code, 201)
        self.assertEqual((cree.json()["prix"], cree.json()["prix_credit"]), (500000, 13.6986))  # nombres, en euros
        pk = cree.json()["id"]
        self.assertEqual(self.appel("patch", f"/api/v1/admin/plans/{pk}/", {"credits": 0}).status_code, 400)
        self.assertEqual(self.appel("patch", f"/api/v1/admin/plans/{pk}/", {"actif": False}).json()["actif"], False)
        self.assertNotIn("Annuel", [p["nom"] for p in self.client.get("/api/v1/plans/").json()])

    @override_settings(BASE_DIR=Path(tempfile.mkdtemp()))
    def test_lancer_suivre_et_suspendre_une_tache(self):
        with mock.patch("apps.offres.services.taches.subprocess.Popen",
                        return_value=mock.Mock(pid=os.getpid())):
            lance = self.appel("post", "/api/v1/admin/taches/lancer/veille/")
            self.assertEqual(lance.status_code, 200)
            deja = self.appel("post", "/api/v1/admin/taches/lancer/trier/")
        self.assertEqual(deja.status_code, 409)  # une tache a la fois
        tache = Tache.objects.get()
        self.assertEqual(self.appel("get", f"/api/v1/admin/taches/{tache.pk}/").json()["statut"], "en_cours")
        self.appel("post", f"/api/v1/admin/taches/{tache.pk}/suspendre/")
        tache.refresh_from_db()
        self.assertEqual(tache.statut, Tache.SUSPENDUE)
        self.assertEqual(self.appel("post", "/api/v1/admin/taches/lancer/rm-rf/").status_code, 400)


class Fumee(Api):

    def test_chaque_route_get_sans_parametre_repond(self):
        from apps.offres.urls import urlpatterns
        offres(2)
        self.connecter_appli("chef@exemple.org", admin=True)
        routes = ["/" + str(p.pattern) for p in urlpatterns
                  if str(p.pattern).startswith("api/v1/") and "<" not in str(p.pattern)]
        self.assertGreater(len(routes), 25)
        for route in routes:
            with self.subTest(route=route):
                code = self.appel("get", route).status_code
                # 405 : route sans GET ; 404 : CV ou photo jamais deposes.
                self.assertIn(code, (200, 404, 405) if route.endswith(("/cv/", "/photo/")) else (200, 405))

    @override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:3000"])
    def test_cors_pour_l_origine_autorisee_seulement(self):
        preflight = self.client.options("/api/v1/moi/", HTTP_ORIGIN="http://localhost:3000",
                                        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
                                        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-session-token")
        self.assertEqual(preflight["Access-Control-Allow-Origin"], "http://localhost:3000")
        self.assertIn("x-session-token", preflight["Access-Control-Allow-Headers"])
        autre = self.client.options("/api/v1/moi/", HTTP_ORIGIN="https://pirate.example",
                                    HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET")
        self.assertNotIn("Access-Control-Allow-Origin", autre)
