"""Tests du backend : protection de l'API, et interface web.

    .\\venv\\Scripts\\python.exe manage.py test apps.offres

Les deux regimes d'authentification sont volontairement etanches -- jeton pour
/api/, session pour l'interface HTML -- et un test le verifie explicitement.

Django cree une base de test separee : ces tests ne touchent jamais les
donnees du pipeline. Le modele Offre etant `managed = False`, sa table y est
posee par config.test_runner.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.offres.services import geo
from apps.offres.auth import empreinte, engendrer
from apps.offres.models import CleApi, Offre, Suivi

#: Toutes les routes de l'API. Une nouvelle ajoutee sans decorateur serait
#: publique sans que rien ne le signale : la liste est donc verifiee ici,
#: et un test compare son contenu aux routes reellement declarees.
LECTURE = ("/api/offres/", "/api/statistiques/", "/api/offres/quelconque/",
           "/api/sources/", "/api/secteurs/", "/api/regions/",
           "/api/carte/points/", "/api/suivi/")
ECRITURE = ("/api/offres/quelconque/decision/", "/api/offres/quelconque/echeance/",
            "/api/offres/quelconque/verdict/")
ENDPOINTS = LECTURE + ECRITURE


class ProtectionParJeton(TestCase):

    def setUp(self):
        self.jeton = engendrer()
        self.cle = CleApi.objects.create(nom="test",
                                         empreinte=empreinte(self.jeton))

    def bearer(self, jeton=None):
        return {"HTTP_AUTHORIZATION": f"Bearer {jeton or self.jeton}"}

    # --- Refus ---

    def test_sans_jeton_tout_est_refuse(self):
        for url in LECTURE:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 401)
        for url in ECRITURE:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, "{}", "application/json").status_code, 401)

    def test_la_liste_des_routes_protegees_est_a_jour(self):
        """Chaque route /api/ declaree doit figurer dans LECTURE ou ECRITURE."""
        from apps.offres.urls import urlpatterns
        declarees = {str(p.pattern) for p in urlpatterns
                     if str(p.pattern).startswith("api/")
                     and not str(p.pattern).startswith("api/public/")}
        couvertes = {u.lstrip("/").replace("quelconque", "<path:offre_id>")
                     for u in ENDPOINTS}
        self.assertEqual(declarees, couvertes)

    def test_un_jeton_inconnu_est_refuse(self):
        reponse = self.client.get("/api/statistiques/", **self.bearer("veille_faux"))
        self.assertEqual(reponse.status_code, 401)

    def test_un_jeton_revoque_est_refuse(self):
        self.cle.revoque_le = timezone.now()
        self.cle.save()
        reponse = self.client.get("/api/statistiques/", **self.bearer())
        self.assertEqual(reponse.status_code, 401)

    def test_le_jeton_en_query_string_ne_compte_pas(self):
        """Une URL se retrouve dans les journaux, l'historique et le Referer."""
        reponse = self.client.get(f"/api/statistiques/?token={self.jeton}")
        self.assertEqual(reponse.status_code, 401)

    def test_le_refus_est_du_json_avec_l_en_tete_attendu(self):
        reponse = self.client.get("/api/statistiques/")
        self.assertEqual(reponse["Content-Type"].split(";")[0], "application/json")
        self.assertIn("Bearer", reponse["WWW-Authenticate"])
        self.assertIn("erreur", reponse.json())

    def test_le_message_ne_dit_pas_pourquoi_le_jeton_est_invalide(self):
        """Distinguer inconnu de revoque renseignerait un attaquant.

        Une seconde cle active maintient le systeme en fonctionnement normal :
        a zero cle active, le message bascule volontairement sur une aide a la
        configuration, qui ne renseigne personne puisque l'API est alors
        inutilisable de toute facon.
        """
        CleApi.objects.create(nom="autre", empreinte=empreinte(engendrer()))
        inconnu = self.client.get("/api/statistiques/",
                                  **self.bearer("veille_faux")).json()["erreur"]
        self.cle.revoque_le = timezone.now()
        self.cle.save()
        revoque = self.client.get("/api/statistiques/", **self.bearer()).json()["erreur"]
        self.assertEqual(inconnu, revoque)

    # --- Acces ---

    def test_un_jeton_valide_ouvre_les_endpoints(self):
        for url in LECTURE:
            if "quelconque" in url:
                continue
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, **self.bearer()).status_code, 200)

    def test_l_en_tete_x_api_key_est_accepte(self):
        reponse = self.client.get("/api/statistiques/", HTTP_X_API_KEY=self.jeton)
        self.assertEqual(reponse.status_code, 200)

    def test_bearer_est_insensible_a_la_casse(self):
        reponse = self.client.get("/api/statistiques/",
                                  HTTP_AUTHORIZATION=f"bearer {self.jeton}")
        self.assertEqual(reponse.status_code, 200)

    def test_l_usage_est_date(self):
        self.assertIsNone(self.cle.derniere_utilisation)
        self.client.get("/api/statistiques/", **self.bearer())
        self.cle.refresh_from_db()
        self.assertIsNotNone(self.cle.derniere_utilisation)


class MethodesDeLApi(TestCase):
    """Les routes de lecture n'ecrivent pas, celles d'ecriture ne se lisent
    pas. Le dire explicitement plutot que de compter sur le middleware CSRF,
    qui rendait un 403 trompeur : la methode n'etait pas refusee, c'est le
    jeton anti-falsification qui manquait.
    """

    def setUp(self):
        self.jeton = engendrer()
        CleApi.objects.create(nom="test", empreinte=empreinte(self.jeton))
        self.entetes = {"HTTP_AUTHORIZATION": f"Bearer {self.jeton}"}

    def test_les_routes_de_lecture_refusent_l_ecriture(self):
        for url in LECTURE:
            for methode in ("post", "put", "patch", "delete"):
                with self.subTest(url=url, methode=methode):
                    appel = getattr(self.client, methode)
                    self.assertEqual(appel(url, **self.entetes).status_code, 405)

    def test_les_routes_d_ecriture_refusent_la_lecture(self):
        for url in ECRITURE:
            for methode in ("get", "put", "patch", "delete"):
                with self.subTest(url=url, methode=methode):
                    appel = getattr(self.client, methode)
                    self.assertEqual(appel(url, **self.entetes).status_code, 405)

    def test_la_methode_prime_sur_le_jeton(self):
        """Un POST sans jeton sur une route de lecture doit dire 405, pas
        401 : la route n'existe pas en ecriture, quel que soit l'appelant."""
        self.assertEqual(self.client.post("/api/offres/").status_code, 405)
        self.assertEqual(self.client.get("/api/offres/x/decision/").status_code, 405)


def _offre(**champs):
    """Une offre de test, retenue et ouverte sauf indication contraire."""
    base = dict(source="test", titre="Offre de test", organisation="Org", description="",
                pays="Madagascar", nature="marche", secteur="informatique",
                categorie="logiciel", raison="test", lien="https://exemple.org",
                pertinent=True, date_limite=timezone.now().date() + timedelta(days=10),
                date_ajout=timezone.now(), date_maj=timezone.now())
    base.update(champs)
    return Offre.objects.create(**base)


class ApiEnLecture(TestCase):
    """Les ressources de lecture rendent ce que l'interface montre."""

    def setUp(self):
        self.jeton = engendrer()
        self.cle = CleApi.objects.create(nom="lecteur", empreinte=empreinte(self.jeton))
        self.entetes = {"HTTP_AUTHORIZATION": f"Bearer {self.jeton}"}
        self.ouverte = _offre(id="t-ouverte", pays="Cameroun", source="cameroun")
        self.mada = _offre(id="t-mada", pays="Madagascar", source="armp",
                           secteur="construction")
        _offre(id="t-close", date_limite=timezone.now().date() - timedelta(days=1))
        _offre(id="t-ecartee", pertinent=False)
        # Sans pays : la base reelle en a, et un tri ou un pays__in naif
        # s'y cassait.
        _offre(id="t-sans-pays", pays=None, source="unjobnet", nature="emploi")
        Suivi.objects.create(offre=self.mada, statut=Suivi.CANDIDATURE, note="en cours")

    def get(self, url):
        reponse = self.client.get(url, **self.entetes)
        self.assertEqual(reponse.status_code, 200, url)
        return reponse.json()

    def test_la_liste_sert_les_actionnables_et_porte_le_suivi(self):
        corps = self.get("/api/offres/")
        self.assertEqual(corps["total"], 3)
        par_id = {o["id"]: o for o in corps["offres"]}
        self.assertEqual(par_id["t-mada"]["suivi"], "candidature")
        self.assertIsNone(par_id["t-ouverte"]["suivi"])
        self.assertEqual(par_id["t-ouverte"]["region"], "afrique")

    def test_les_interrupteurs_elargissent_la_vue(self):
        self.assertEqual(self.get("/api/offres/?cloturees=1")["total"], 4)
        self.assertEqual(self.get("/api/offres/?ecartees=1")["total"], 4)
        self.assertEqual(self.get("/api/offres/?ecartees=1&cloturees=1")["total"], 5)

    def test_le_filtre_de_region_et_de_suivi(self):
        self.assertEqual([o["id"] for o in self.get("/api/offres/?region=afrique")["offres"]],
                         ["t-ouverte"])
        self.assertEqual([o["id"] for o in self.get("/api/offres/?region=madagascar")["offres"]],
                         ["t-mada"])
        self.assertEqual(self.get("/api/offres/?suivi=candidature")["total"], 1)
        self.assertEqual(self.get("/api/offres/?suivi=aucun")["total"], 2)
        self.assertEqual([o["id"] for o in self.get("/api/offres/?region=inconnue")["offres"]],
                         ["t-sans-pays"])

    def test_la_fiche_detaille_le_suivi(self):
        corps = self.get("/api/offres/t-mada/")
        self.assertEqual(corps["suivi"]["statut_libelle"], "Candidature déposée")
        self.assertEqual(corps["suivi"]["note"], "en cours")
        self.assertIn("description", corps)

    def test_sources_secteurs_regions(self):
        sources = {s["source"]: s for s in self.get("/api/sources/")["sources"]}
        self.assertEqual(sources["test"]["total"], 2)
        self.assertEqual(sources["test"]["actionnables"], 0)
        self.assertEqual(sources["cameroun"]["actionnables"], 1)
        secteurs = {s["code"]: s for s in self.get("/api/secteurs/")["secteurs"]}
        self.assertEqual(secteurs["construction"]["actionnables"], 1)
        self.assertEqual(len(secteurs), 5)
        regions_ = {r["code"]: r for r in self.get("/api/regions/")["regions"]}
        self.assertIn("Cameroun", regions_["afrique"]["lieux"])
        self.assertEqual(regions_["afrique"]["actionnables"], 1)
        self.assertEqual(regions_["inconnue"]["lieux"], [], "un pays absent n'a pas de nom")
        self.assertEqual(regions_["inconnue"]["actionnables"], 1, "mais ses offres se comptent")

    def test_la_carte_et_le_suivi(self):
        carte = self.get("/api/carte/points/")
        self.assertEqual(carte["total"], 2)
        self.assertEqual(carte["sans_position"], 1)
        self.assertIn(carte["points"][0]["lieu"], ("Madagascar", "Cameroun"))
        suivi = self.get("/api/suivi/?statut=candidature")
        self.assertEqual(suivi["total"], 1)
        self.assertEqual(suivi["suivis"][0]["offre"]["id"], "t-mada")

    def test_les_statistiques_comptent_par_region(self):
        corps = self.get("/api/statistiques/")
        self.assertEqual(corps["par_region"]["madagascar"], 2, "les retenues, pas les ecartees")
        self.assertEqual(corps["par_region"]["inconnue"], 1)
        self.assertEqual(corps["actionnables"], 3)


class ApiEnEcriture(TestCase):
    """Les decisions par l'API : validees, tracees, et refusees sans jeton."""

    def setUp(self):
        self.jeton = engendrer()
        self.cle = CleApi.objects.create(nom="n8n", empreinte=empreinte(self.jeton))
        self.entetes = {"HTTP_AUTHORIZATION": f"Bearer {self.jeton}"}
        self.offre = _offre(id="t-1", date_limite=None)

    def post(self, url, corps):
        import json
        return self.client.post(url, json.dumps(corps), content_type="application/json",
                                **self.entetes)

    def test_une_decision_cree_le_suivi_et_nomme_la_cle(self):
        reponse = self.post("/api/offres/t-1/decision/", {"statut": "candidature", "note": "devis envoye"})
        self.assertEqual(reponse.status_code, 201)
        suivi = Suivi.objects.get(offre=self.offre)
        self.assertEqual(suivi.statut, Suivi.CANDIDATURE)
        self.assertEqual(suivi.note, "devis envoye")
        self.assertEqual(suivi.decide_par_cle, self.cle)
        self.assertIsNone(suivi.decide_par)
        self.assertEqual(reponse.json()["suivi"]["decide_par_cle"], "n8n")

    def test_une_seconde_decision_met_a_jour(self):
        self.post("/api/offres/t-1/decision/", {"statut": "a_etudier", "note": "a lire"})
        reponse = self.post("/api/offres/t-1/decision/", {"statut": "perdu"})
        self.assertEqual(reponse.status_code, 200)
        suivi = Suivi.objects.get(offre=self.offre)
        self.assertEqual(suivi.statut, Suivi.PERDU)
        self.assertEqual(suivi.note, "a lire", "une note absente laisse la note en place")
        self.post("/api/offres/t-1/decision/", {"statut": "perdu", "note": ""})
        self.assertEqual(Suivi.objects.get(offre=self.offre).note, "", "une note vide efface")

    def test_un_statut_inconnu_ou_un_corps_illisible_est_refuse(self):
        self.assertEqual(self.post("/api/offres/t-1/decision/", {"statut": "gagnant"}).status_code, 400)
        reponse = self.client.post("/api/offres/t-1/decision/", "pas du json",
                                   content_type="application/json", **self.entetes)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("JSON", reponse.json()["erreur"])
        self.assertEqual(self.post("/api/offres/t-1/decision/", ["liste"]).status_code, 400)
        self.assertEqual(self.post("/api/offres/t-1/decision/",
                                   {"statut": "gagne", "note": "x" * 2001}).status_code, 400)
        self.assertFalse(Suivi.objects.exists())

    def test_l_echeance_est_ecrite_aux_deux_endroits(self):
        reponse = self.post("/api/offres/t-1/echeance/", {"echeance": "2026-10-01"})
        self.assertEqual(reponse.status_code, 200)
        self.offre.refresh_from_db()
        self.assertEqual(str(self.offre.date_limite), "2026-10-01")
        suivi = Suivi.objects.get(offre=self.offre)
        self.assertEqual(str(suivi.echeance), "2026-10-01")
        self.assertIsNotNone(suivi.echeance_saisie_le)
        self.assertEqual(suivi.decide_par_cle, self.cle)

    def test_une_date_illisible_est_refusee(self):
        for corps in ({"echeance": "01/10/2026"}, {"echeance": 20261001}, {}):
            with self.subTest(corps=corps):
                self.assertEqual(self.post("/api/offres/t-1/echeance/", corps).status_code, 400)
        self.offre.refresh_from_db()
        self.assertIsNone(self.offre.date_limite)

    def test_le_verdict_bascule_pertinent(self):
        self.assertEqual(self.post("/api/offres/t-1/verdict/", {"pertinent": False}).status_code, 200)
        self.offre.refresh_from_db()
        self.assertFalse(self.offre.pertinent)
        self.assertEqual(self.post("/api/offres/t-1/verdict/", {"pertinent": "oui"}).status_code, 400)

    def test_une_offre_inconnue_rend_404(self):
        self.assertEqual(self.post("/api/offres/inconnue/decision/", {"statut": "gagne"}).status_code, 404)

    def test_sans_jeton_rien_n_est_ecrit(self):
        reponse = self.client.post("/api/offres/t-1/decision/", '{"statut": "gagne"}',
                                   content_type="application/json")
        self.assertEqual(reponse.status_code, 401)
        self.assertFalse(Suivi.objects.exists())

    def test_une_session_web_ne_suffit_pas(self):
        """Le regime est le jeton, meme pour une personne connectee a l'ecran :
        l'API n'est pas une porte derobee de l'interface, ni l'inverse."""
        User.objects.create_user("testeur", password="mot-de-passe-de-test")
        self.client.login(username="testeur", password="mot-de-passe-de-test")
        reponse = self.client.post("/api/offres/t-1/decision/", '{"statut": "gagne"}',
                                   content_type="application/json")
        self.assertEqual(reponse.status_code, 401)


class ApiPublique(TestCase):
    """/api/public/ : sans jeton, sans suivi, sans ecartees, avec la position."""

    def setUp(self):
        self.ouverte = _offre(id="p-cam", pays="Cameroun", source="cameroun",
                              description="Fourniture de serveurs")
        self.mada = _offre(id="p-mada", pays="Madagascar", source="armp",
                           date_limite=timezone.now().date() + timedelta(days=3))
        _offre(id="p-close", date_limite=timezone.now().date() - timedelta(days=1))
        _offre(id="p-ecartee", pertinent=False)
        _offre(id="p-unjobnet", source="unjobnet", nature="emploi", pays=None)
        Suivi.objects.create(offre=self.mada, statut=Suivi.CANDIDATURE, note="secret")

    def get(self, url):
        reponse = self.client.get(url)
        self.assertEqual(reponse.status_code, 200, url)
        return reponse

    def test_aucun_jeton_n_est_demande(self):
        for url in ("/api/public/", "/api/public/offres/", "/api/public/offres/p-cam/",
                    "/api/public/statistiques/", "/api/public/sources/", "/api/public/secteurs/",
                    "/api/public/regions/", "/api/public/lieux/", "/api/public/carte/points/"):
            with self.subTest(url=url):
                self.get(url)

    def test_le_suivi_commercial_ne_sort_jamais(self):
        for url in ("/api/public/offres/", "/api/public/offres/p-mada/", "/api/public/statistiques/"):
            with self.subTest(url=url):
                corps = self.get(url).content.decode()
                self.assertNotIn("suivi", corps)
                self.assertNotIn("candidature", corps)
                self.assertNotIn("secret", corps)

    def test_les_ecartees_sont_invisibles_meme_par_leur_id(self):
        ids = {o["id"] for o in self.get("/api/public/offres/?cloturees=1").json()["offres"]}
        self.assertNotIn("p-ecartee", ids)
        self.assertEqual(self.client.get("/api/public/offres/p-ecartee/").status_code, 404)

    def test_par_defaut_les_ouvertes_seulement(self):
        ids = {o["id"] for o in self.get("/api/public/offres/").json()["offres"]}
        self.assertEqual(ids, {"p-cam", "p-mada", "p-unjobnet"})
        ids = {o["id"] for o in self.get("/api/public/offres/?cloturees=1").json()["offres"]}
        self.assertIn("p-close", ids)

    def test_la_localisation_accompagne_chaque_offre(self):
        par_id = {o["id"]: o for o in self.get("/api/public/offres/").json()["offres"]}
        cam = par_id["p-cam"]["localisation"]
        self.assertEqual(cam["region"], "afrique")
        self.assertEqual(cam["region_libelle"], "Afrique")
        self.assertAlmostEqual(cam["lat"], 7.4)
        self.assertAlmostEqual(cam["lon"], 12.4)
        sans = par_id["p-unjobnet"]["localisation"]
        self.assertIsNone(sans["lieu"])
        self.assertIsNone(sans["lat"])
        self.assertEqual(sans["region"], "inconnue")
        self.assertTrue(par_id["p-mada"]["urgente"])
        self.assertFalse(par_id["p-cam"]["urgente"])

    def test_la_fiche_porte_la_description(self):
        corps = self.get("/api/public/offres/p-cam/").json()
        self.assertEqual(corps["description"], "Fourniture de serveurs")
        self.assertIn("raison", corps)
        self.assertNotIn("description", self.get("/api/public/offres/").json()["offres"][0])

    def test_tri_urgence_et_recherche(self):
        ids = [o["id"] for o in self.get("/api/public/offres/?tri=echeance").json()["offres"]]
        self.assertEqual(ids[0], "p-mada")
        self.assertEqual([o["id"] for o in self.get("/api/public/offres/?urgence=7").json()["offres"]],
                         ["p-mada"])
        self.assertEqual([o["id"] for o in self.get("/api/public/offres/?q=serveurs").json()["offres"]],
                         ["p-cam"], "la recherche porte aussi sur la description")

    def test_une_source_exclue_disparait_partout(self):
        with self.settings(API_PUBLIQUE_SOURCES_EXCLUES=["unjobnet"]):
            ids = {o["id"] for o in self.get("/api/public/offres/").json()["offres"]}
            self.assertNotIn("p-unjobnet", ids)
            self.assertEqual(self.client.get("/api/public/offres/p-unjobnet/").status_code, 404)
            self.assertNotIn("unjobnet", self.get("/api/public/statistiques/").json()["par_source"])
            self.assertNotIn("unjobnet", [s["source"] for s in self.get("/api/public/sources/").json()["sources"]])
            self.assertEqual(self.get("/api/public/").json()["sources_exclues"], ["unjobnet"])

    def test_lieux_regions_carte(self):
        lieux = {l["lieu"]: l for l in self.get("/api/public/lieux/").json()["lieux"]}
        self.assertEqual(lieux["Cameroun"]["ouvertes"], 1)
        self.assertAlmostEqual(lieux["Madagascar"]["lat"], -18.9)
        regions_ = {r["code"]: r for r in self.get("/api/public/regions/").json()["regions"]}
        self.assertEqual(regions_["afrique"]["ouvertes"], 1)
        carte = self.get("/api/public/carte/points/?region=madagascar").json()
        self.assertEqual(carte["total"], 1)
        self.assertEqual(carte["points"][0]["lieu"], "Madagascar")

    def test_cors_cache_et_preverification(self):
        reponse = self.get("/api/public/offres/")
        self.assertEqual(reponse["Access-Control-Allow-Origin"], "*")
        self.assertIn("max-age", reponse["Cache-Control"])
        options = self.client.options("/api/public/offres/")
        self.assertEqual(options.status_code, 204)
        self.assertEqual(options["Access-Control-Allow-Methods"], "GET, OPTIONS")
        with self.settings(API_PUBLIQUE_ORIGINES="https://site.exemple"):
            self.assertEqual(self.get("/api/public/")["Access-Control-Allow-Origin"],
                             "https://site.exemple")

    def test_l_ecriture_est_refusee(self):
        for methode in ("post", "put", "patch", "delete"):
            with self.subTest(methode=methode):
                self.assertEqual(getattr(self.client, methode)("/api/public/offres/").status_code, 405)

    def test_l_index_nomme_toutes_les_routes(self):
        routes = self.get("/api/public/").json()["routes"]
        self.assertEqual(set(routes), {"offres", "offre", "statistiques", "sources",
                                       "secteurs", "regions", "lieux", "carte"})
        self.assertTrue(routes["offres"]["url"].endswith("/api/public/offres/"))


class StockageDuJeton(TestCase):

    def test_le_jeton_n_est_jamais_stocke(self):
        """Une fuite de la base ne doit livrer aucun acces."""
        jeton = engendrer()
        CleApi.objects.create(nom="test", empreinte=empreinte(jeton))
        for valeur in CleApi.objects.values_list(flat=False).first():
            self.assertNotIn(jeton, str(valeur))

    def test_deux_jetons_engendres_different(self):
        self.assertNotEqual(engendrer(), engendrer())

    def test_le_jeton_porte_son_prefixe_et_assez_d_alea(self):
        jeton = engendrer()
        self.assertTrue(jeton.startswith(CleApi.PREFIXE))
        # 32 octets en base64 URL-safe : 43 caracteres.
        self.assertGreaterEqual(len(jeton) - len(CleApi.PREFIXE), 43)


class ApiFermeeSansCle(TestCase):

    def test_sans_aucune_cle_l_api_reste_fermee(self):
        """Une API qui s'ouvrirait faute de cle serait le contraire du but."""
        self.assertFalse(CleApi.objects.exists())
        reponse = self.client.get("/api/statistiques/",
                                  HTTP_AUTHORIZATION="Bearer veille_quelconque")
        self.assertEqual(reponse.status_code, 401)
        self.assertIn("cle_api", reponse.json()["erreur"])


class InterfaceWeb(TestCase):
    """L'interface HTML : session, pas jeton.

    Elle s'adresse a une personne devant un navigateur. Un jeton d'API
    n'aurait aucun sens ici, il faudrait le coller dans un en-tete a chaque
    page.
    """

    def setUp(self):
        self.utilisateur = User.objects.create_user("testeur", password="mot-de-passe-de-test")
        Offre.objects.create(
            id="conservation-abc", source="conservation",
            titre="Biodiversity Hotspots Global Platform: Website Design",
            organisation="Conservation International", pays="International",
            date_limite=timezone.now().date() + timedelta(days=14),
            pertinent=True, nature="marche", secteur="informatique",
            categorie="developpement web",
            raison="Developpement de plateforme", lien="https://exemple.org/a.pdf",
            date_ajout=timezone.now(), date_maj=timezone.now())
        Offre.objects.create(
            id="unjobnet-xyz", source="unjobnet", titre="Software Developer",
            organisation="PNUD", pays="Madagascar",
            date_limite=timezone.now().date() + timedelta(days=3),
            pertinent=True, nature="emploi", secteur="informatique",
            categorie="poste",
            raison="Poste salarie", lien="https://exemple.org/b",
            date_ajout=timezone.now(), date_maj=timezone.now())
        Offre.objects.create(
            id="bad-ecartee", source="bad", titre="Fourniture de ciment",
            organisation="BAD", pays="Niger", date_limite=None,
            pertinent=False, nature="marche", secteur="construction",
            categorie="travaux",
            raison="Hors perimetre", lien="https://exemple.org/c",
            date_ajout=timezone.now(), date_maj=timezone.now())

    def connecter(self):
        self.client.login(username="testeur", password="mot-de-passe-de-test")

    # --- Acces ---

    def test_l_interface_est_ouverte_sans_compte(self):
        """Application mono-utilisateur : ni connexion ni inscription."""
        for url in ("/", "/offre/conservation-abc/", "/suivi/", "/a-dater/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get("/comptes/login/").status_code, 404)

    def test_une_decision_sans_compte_n_a_pas_d_auteur(self):
        self.client.post("/offre/conservation-abc/decider/", {"statut": "candidature"})
        suivi = Suivi.objects.get(offre_id="conservation-abc")
        self.assertEqual(suivi.statut, "candidature")
        self.assertIsNone(suivi.decide_par)

    # --- Liste ---

    def test_la_liste_montre_les_actionnables_par_defaut(self):
        self.connecter()
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Biodiversity Hotspots")
        self.assertContains(reponse, "Software Developer")
        # L'ecartee n'a pas sa place dans la vue par defaut.
        self.assertNotContains(reponse, "Fourniture de ciment")

    def test_le_filtre_de_nature_separe_marches_et_postes(self):
        self.connecter()
        marches = self.client.get("/?nature=marche")
        self.assertContains(marches, "Biodiversity Hotspots")
        self.assertNotContains(marches, "Software Developer")
        postes = self.client.get("/?nature=emploi")
        self.assertContains(postes, "Software Developer")
        self.assertNotContains(postes, "Biodiversity Hotspots")

    def test_les_ecartees_sont_accessibles_a_la_demande(self):
        self.connecter()
        reponse = self.client.get("/?etat=ecartees")
        self.assertContains(reponse, "Fourniture de ciment")
        self.assertNotContains(reponse, "Biodiversity Hotspots")

    def test_la_recherche_porte_sur_plusieurs_champs(self):
        self.connecter()
        self.assertContains(self.client.get("/?q=Biodiversity"), "Biodiversity Hotspots")
        self.assertContains(self.client.get("/?q=PNUD"), "Software Developer")
        self.assertContains(self.client.get("/?q=developpement"), "Biodiversity Hotspots")

    def test_une_recherche_infructueuse_le_dit(self):
        self.connecter()
        reponse = self.client.get("/?q=zzzzintrouvable")
        self.assertContains(reponse, "Aucune offre")

    def test_les_compteurs_suivent_la_selection(self):
        """Ils decrivent ce que l'on regarde, pas toute la base."""
        self.connecter()
        tout = self.client.get("/").context["compte"]
        self.assertEqual(tout["total"], 2)
        self.assertEqual(tout["informatique"], 2)
        filtre = self.client.get("/?nature=marche").context["compte"]
        self.assertEqual(filtre["total"], 1)

    # --- Echeances ---

    def test_l_echeance_proche_est_signalee(self):
        self.connecter()
        offres = {o.id: o for o in self.client.get("/").context["page"]}
        self.assertEqual(offres["unjobnet-xyz"].etat_echeance, "urgente")
        self.assertEqual(offres["conservation-abc"].etat_echeance, "proche")

    def test_une_offre_sans_echeance_reste_actionnable(self):
        """Toute la source BAD est dans ce cas : la date est dans le PDF."""
        self.connecter()
        reponse = self.client.get("/?etat=ecartees")
        offre = reponse.context["page"][0]
        self.assertEqual(offre.etat_echeance, "inconnue")

    # --- Fiche ---

    def test_la_fiche_montre_le_verdict_et_le_lien(self):
        self.connecter()
        reponse = self.client.get("/offre/conservation-abc/")
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Developpement de plateforme")
        self.assertContains(reponse, "https://exemple.org/a.pdf")
        self.assertContains(reponse, "Retenue")

    def test_une_fiche_inexistante_rend_404(self):
        self.connecter()
        self.assertEqual(self.client.get("/offre/nexiste-pas/").status_code, 404)


class Regions(TestCase):
    """La region est deduite du champ `pays`, jamais stockee."""

    def test_les_lieux_courants_sont_classes(self):
        cas = {
            "Madagascar": geo.MADAGASCAR,
            "La Réunion (France)": geo.OCEAN_INDIEN,
            "Mayotte (France)": geo.OCEAN_INDIEN,
            "Maurice": geo.OCEAN_INDIEN,
            "Nairobi": geo.AFRIQUE,
            "RDC": geo.AFRIQUE,
            "The Hague": geo.EUROPE,
            "Washington DC": geo.AMERIQUES,
            "Bangkok": geo.ASIE_PACIFIQUE,
            "Damascus": geo.MOYEN_ORIENT,
            "Multinational": geo.INTERNATIONAL,
            "": geo.INCONNUE,
        }
        for lieu, attendu in cas.items():
            with self.subTest(lieu=lieu):
                self.assertEqual(geo.region(lieu), attendu)

    def test_les_deux_apostrophes_donnent_le_meme_pays(self):
        """Les donnees portent les deux graphies : droite et courbe."""
        droite = geo.region("Côte d'Ivoire")
        courbe = geo.region("Côte d’Ivoire")
        self.assertEqual(droite, courbe)
        self.assertEqual(droite, geo.AFRIQUE)

    def test_l_accent_ne_separe_pas_deux_graphies(self):
        self.assertEqual(geo.region("Sénégal"), geo.region("Senegal"))

    def test_la_recherche_porte_sur_des_mots_entiers(self):
        """Une inclusion brute rangerait Tirana au Moyen-Orient -- "iran" y
        figure comme sous-chaine -- et Romania de meme par "oman"."""
        self.assertNotEqual(geo.region("Tirana"), geo.MOYEN_ORIENT)
        self.assertNotEqual(geo.region("Romania"), geo.MOYEN_ORIENT)

    def test_le_lieu_le_plus_long_gagne(self):
        """Sans cela "guinee" l'emporterait sur "guinee bissau"."""
        self.assertEqual(geo.region("Nigeria"), geo.AFRIQUE)
        self.assertEqual(geo.region("Nigeria, Abuja"), geo.AFRIQUE)

    def test_un_lieu_compose_est_reconnu_par_repli(self):
        self.assertEqual(geo.region("Bureau de Nairobi"), geo.AFRIQUE)
        self.assertEqual(geo.region("Antananarivo, Madagascar"),
                         geo.MADAGASCAR)

    def test_chaque_region_a_un_libelle(self):
        """Le gabarit fait LIBELLE[region] : une region sans libelle serait
        une KeyError en pleine page."""
        for code in set(geo.CORRESPONDANCE.values()) | {geo.INCONNUE}:
            self.assertIn(code, geo.LIBELLE)

    def test_repartir_regroupe_sans_rien_perdre(self):
        lieux = ["Madagascar", "Maurice", "Nairobi", "", "Zzzz inconnu"]
        par_region = geo.repartir(lieux)
        self.assertEqual(sum(len(v) for v in par_region.values()), len(lieux))
        self.assertIn("Madagascar", par_region[geo.MADAGASCAR])


class FiltreRegion(TestCase):

    def setUp(self):
        self.utilisateur = User.objects.create_user("testeur", password="mdp-de-test")
        for oid, pays in [("a", "Madagascar"), ("b", "La Réunion (France)"),
                          ("c", "Nairobi"), ("d", "")]:
            Offre.objects.create(
                id=oid, source="test", titre=f"Offre {oid}", organisation="O",
                pays=pays, date_limite=None, pertinent=True, nature="marche",
                secteur="informatique", categorie="c", raison="r",
                lien="https://exemple.org",
                date_ajout=timezone.now(), date_maj=timezone.now())
        self.client.login(username="testeur", password="mdp-de-test")

    def test_le_filtre_ne_retient_que_la_region_demandee(self):
        reponse = self.client.get("/?region=madagascar")
        titres = [o.titre for o in reponse.context["page"]]
        self.assertEqual(titres, ["Offre a"])

    def test_l_ocean_indien_et_madagascar_sont_distincts(self):
        """Madagascar a sa propre region : c'est le marche domestique."""
        oi = [o.titre for o in self.client.get("/?region=ocean-indien").context["page"]]
        self.assertEqual(oi, ["Offre b"])

    def test_un_lieu_vide_tombe_en_region_inconnue(self):
        r = [o.titre for o in self.client.get("/?region=inconnue").context["page"]]
        self.assertEqual(r, ["Offre d"])

    def test_une_region_inventee_ne_filtre_rien(self):
        """Mieux vaut tout montrer qu'une page vide sans explication."""
        reponse = self.client.get("/?region=atlantide")
        self.assertEqual(len(reponse.context["page"]), 4)

    def test_le_filtre_par_lieu_exact_fonctionne(self):
        """C'est ce que la carte passe quand on clique un point : elle
        designe un lieu precis, pas une region."""
        reponse = self.client.get("/?lieu=Madagascar")
        titres = [o.titre for o in reponse.context["page"]]
        self.assertEqual(titres, ["Offre a"])

    def test_le_lieu_filtre_est_annonce_et_retirable(self):
        """Le lieu n'a pas de selecteur dans le formulaire : sans bandeau, on
        ne comprendrait pas pourquoi la liste est courte."""
        reponse = self.client.get("/?lieu=Madagascar&nature=marche")
        self.assertContains(reponse, "Madagascar")
        self.assertContains(reponse, "retirer ce filtre")
        # Le lien de retrait garde les autres filtres et perd le lieu.
        sans = reponse.context["parametres_sans_lieu"]
        self.assertIn("nature=marche", sans)
        self.assertNotIn("lieu=", sans)

    def test_un_lieu_a_parentheses_et_accents_se_filtre(self):
        """"La Réunion (France)" doit survivre a l'aller-retour dans l'URL."""
        reponse = self.client.get("/", {"lieu": "La Réunion (France)"})
        titres = [o.titre for o in reponse.context["page"]]
        self.assertEqual(titres, ["Offre b"])

    def test_la_colonne_apparait_dans_la_page(self):
        reponse = self.client.get("/")
        self.assertContains(reponse, "Région")
        self.assertContains(reponse, "reg-madagascar")


class Carte(TestCase):
    """Un point par LIEU, pas par offre : cent marqueurs superposes sur
    Madagascar ne se distingueraient pas."""

    def setUp(self):
        User.objects.create_user("testeur", password="mdp-de-test")
        for oid, pays, nature, jours in [
                ("a", "Madagascar", "marche", 30),
                ("b", "Madagascar", "emploi", 3),
                ("c", "Nairobi", "marche", 40),
                ("d", "Multinational", "marche", 40)]:
            Offre.objects.create(
                id=oid, source="test", titre=f"Offre {oid}", organisation="O",
                pays=pays, date_limite=timezone.now().date() + timedelta(days=jours),
                pertinent=True, nature=nature, secteur="informatique",
                categorie="c", raison="r", lien="https://exemple.org",
                date_ajout=timezone.now(), date_maj=timezone.now())
        self.client.login(username="testeur", password="mdp-de-test")

    def points(self, requete=""):
        return self.client.get("/carte/points/" + requete).json()

    def test_la_page_est_ouverte_sans_compte(self):
        self.client.logout()
        for url in ("/carte/", "/carte/points/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_les_offres_sont_regroupees_par_lieu(self):
        d = self.points()
        lieux = {p["lieu"]: p for p in d["points"]}
        self.assertEqual(lieux["Madagascar"]["total"], 2)
        self.assertEqual(lieux["Madagascar"]["marches"], 1)
        self.assertEqual(lieux["Madagascar"]["emplois"], 1)

    def test_un_lieu_non_localisable_est_compte_pas_place(self):
        """"Multinational" ne designe aucun point : le taire donnerait une
        carte qui ment sur le total."""
        d = self.points()
        self.assertNotIn("Multinational", [p["lieu"] for p in d["points"]])
        self.assertEqual(d["sans_position"], 1)

    def test_les_points_portent_leur_region(self):
        lieux = {p["lieu"]: p for p in self.points()["points"]}
        self.assertEqual(lieux["Madagascar"]["region"], "Madagascar")
        self.assertEqual(lieux["Nairobi"]["region"], "Afrique")

    def test_l_urgence_est_signalee(self):
        lieux = {p["lieu"]: p for p in self.points()["points"]}
        self.assertEqual(lieux["Madagascar"]["urgentes"], 1)
        self.assertEqual(lieux["Nairobi"]["urgentes"], 0)

    def test_la_carte_obeit_aux_memes_filtres_que_la_liste(self):
        """Passer de la liste a la carte ne doit pas changer ce que l'on
        regarde."""
        d = self.points("?nature=emploi")
        self.assertEqual([p["lieu"] for p in d["points"]], ["Madagascar"])
        self.assertEqual(d["total"], 1)
        d = self.points("?region=afrique")
        self.assertEqual([p["lieu"] for p in d["points"]], ["Nairobi"])

    def test_les_points_sont_ordonnes_du_plus_gros_au_plus_petit(self):
        totaux = [p["total"] for p in self.points()["points"]]
        self.assertEqual(totaux, sorted(totaux, reverse=True))

    def test_la_page_ne_fait_aucun_appel_externe(self):
        """Le fond de carte est embarque : la page doit fonctionner hors ligne.

        La version precedente chargeait Leaflet et les tuiles OpenStreetMap.
        Sans reseau, la carte etait vide -- c'est la panne qui a motive ce
        changement.
        """
        page = self.client.get("/carte/").content.decode("utf-8")
        # Les seuls "http://" toleres sont des IDENTIFIANTS d'espace de noms
        # XML. Ce sont des chaines conventionnelles, jamais telechargees : un
        # navigateur hors ligne les traite exactement pareil.
        reste = page
        # Tailwind et HTMX viennent d'un CDN, a version epinglee (instructions.md) :
        # ce sont les seules exceptions, le fond de carte reste embarque.
        for espace_de_noms in ("http://www.w3.org/2000/svg",
                               "http://www.w3.org/1999/xlink",
                               "https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4.1.11/dist/index.global.js",
                               "https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js"):
            reste = reste.replace(espace_de_noms, "")
        self.assertNotIn("http://", reste)
        self.assertNotIn("https://", reste)
        self.assertNotIn("leaflet", page.lower())

    def test_le_fond_de_carte_est_present(self):
        page = self.client.get("/carte/").content.decode("utf-8")
        self.assertIn('id="continents"', page)
        self.assertIn('viewBox="0 0 2000 800"', page)
        # 177 pays dans Natural Earth 110m ; en perdre signalerait un fond
        # tronque.
        self.assertGreater(page.count("<path d="), 150)

    def test_chaque_point_est_un_lien_vers_ses_offres(self):
        """Cliquer un point doit OUVRIR la liste du lieu, pas une fiche.

        La version precedente montrait trois exemples et s'arretait la : un
        cul-de-sac. Le lien est un <a> SVG, donc ouvrable dans un onglet et
        atteignable au clavier sans qu'on ait a le reimplementer.
        """
        page = self.client.get("/carte/").content.decode("utf-8")
        self.assertIn('createElementNS(SVG, "a")', page)
        self.assertIn("lienListe", page)
        # La fiche intermediaire ne doit plus exister.
        self.assertNotIn("montrerFiche", page)
        self.assertNotIn("fiche-lieu", page)

    def test_le_pointeur_n_est_capture_qu_apres_un_deplacement(self):
        """Le clic doit atteindre le lien du point.

        La premiere version appelait setPointerCapture des le pointerdown.
        Tous les evenements etaient alors detournes vers le <svg> et le clic
        n'atteignait jamais le <a> : la page ne s'ouvrait pas. La capture
        n'a desormais lieu qu'une fois le deplacement avere, au-dela d'un
        seuil de quelques pixels.
        """
        page = self.client.get("/carte/").content.decode("utf-8")
        debut = page.index('addEventListener("pointerdown"')
        fin = page.index('addEventListener("pointermove"')
        self.assertNotIn("setPointerCapture", page[debut:fin],
                         "le pointeur est capture des l'appui")
        self.assertIn("SEUIL_GLISSE", page)

    def test_le_lien_est_pose_sous_les_deux_formes(self):
        """href pour SVG 2, xlink:href pour les moteurs anciens. Un lien mort
        ne se voit pas, il ne fait simplement rien."""
        page = self.client.get("/carte/").content.decode("utf-8")
        self.assertIn('setAttribute("href", url)', page)
        self.assertIn("xlink:href", page)

    def test_le_lien_reprend_les_filtres_courants(self):
        """Cliquer un point ne doit pas elargir en douce ce qu'on regardait."""
        page = self.client.get("/carte/?nature=marche").content.decode("utf-8")
        self.assertIn("nature=marche", page)
        self.assertIn("FILTRES_COURANTS", page)

    def test_l_infobulle_ne_porte_que_trois_exemples(self):
        """Au-dela, elle deviendrait une page."""
        for i in range(6):
            Offre.objects.create(
                id=f"extra{i}", source="test", titre=f"Extra {i}",
                organisation="O", pays="Madagascar", date_limite=None,
                pertinent=True, nature="marche", secteur="informatique",
                categorie="c", raison="r", lien="https://exemple.org",
                date_ajout=timezone.now(), date_maj=timezone.now())
        lieux = {p["lieu"]: p for p in self.points()["points"]}
        self.assertEqual(len(lieux["Madagascar"]["exemples"]), 3)
        self.assertEqual(lieux["Madagascar"]["total"], 8)


class Coordonnees(TestCase):

    def test_les_lieux_courants_sont_places(self):
        for lieu in ("Madagascar", "La Réunion (France)", "Nairobi",
                     "The Hague", "Washington DC", "Côte d'Ivoire"):
            with self.subTest(lieu=lieu):
                self.assertIsNotNone(geo.point(lieu))

    def test_une_mention_collective_n_a_pas_de_point(self):
        for lieu in ("Multinational", "International", ""):
            with self.subTest(lieu=lieu):
                self.assertIsNone(geo.point(lieu))

    def test_les_coordonnees_sont_dans_les_bornes(self):
        """Une latitude hors [-90, 90] passerait inapercue et poserait le
        point n'importe ou."""
        for cle, (lat, lon) in geo.COORDONNEES.items():
            with self.subTest(lieu=cle):
                self.assertTrue(-90 <= lat <= 90, f"{cle} : latitude {lat}")
                self.assertTrue(-180 <= lon <= 180, f"{cle} : longitude {lon}")

    def test_madagascar_est_bien_dans_l_ocean_indien(self):
        """Garde-fou contre une inversion latitude/longitude, l'erreur la plus
        facile a commettre et la plus difficile a voir dans une table."""
        lat, lon = geo.point("Madagascar")
        self.assertTrue(-26 < lat < -11, f"latitude {lat}")
        self.assertTrue(43 < lon < 51, f"longitude {lon}")


class CleDeSignature(TestCase):
    """La cle qui signe les sessions doit etre STABLE d'un demarrage a l'autre.

    Une premiere version l'engendrait a chaque lancement. Le secret ne fuitait
    pas, mais chaque redemarrage du serveur invalidait les sessions --
    "Session data corrupted" dans le journal, et l'utilisateur renvoye vers la
    connexion sans comprendre. Le symptome se lisait "rien ne marche".
    """


    def test_la_cle_ne_change_pas_entre_deux_lectures(self):
        from django.conf import settings
        premiere = settings.SECRET_KEY
        seconde = settings.FICHIER_CLE.read_text(encoding="utf-8").strip()
        self.assertEqual(premiere, seconde)

    def test_la_cle_a_assez_d_alea(self):
        from django.conf import settings
        self.assertGreaterEqual(len(settings.SECRET_KEY), 43)


class FiltreSecteur(TestCase):
    """Les trois domaines suivis, filtrables separement.

    Ils ont ete ajoutes ensemble a la demande : sans separation, la
    construction et l'agriculture -- bien plus volumineuses -- noieraient
    l'informatique dans la liste par defaut.
    """

    def setUp(self):
        User.objects.create_user("testeur", password="mdp-de-test")
        for oid, secteur in [("i", "informatique"), ("c", "construction"),
                             ("a", "agriculture"), ("e", "eau"),
                             ("v", "environnement")]:
            Offre.objects.create(
                id=oid, source="test", titre=f"Offre {oid}", organisation="O",
                pays="Madagascar", date_limite=None, pertinent=True,
                nature="marche", secteur=secteur, categorie="c", raison="r",
                lien="https://exemple.org",
                date_ajout=timezone.now(), date_maj=timezone.now())
        self.client.login(username="testeur", password="mdp-de-test")

    def test_chaque_secteur_se_filtre(self):
        for secteur, attendu in [("informatique", "Offre i"),
                                 ("construction", "Offre c"),
                                 ("agriculture", "Offre a"),
                                 ("eau", "Offre e"),
                                 ("environnement", "Offre v")]:
            with self.subTest(secteur=secteur):
                page = self.client.get(f"/?secteur={secteur}").context["page"]
                self.assertEqual([o.titre for o in page], [attendu])

    def test_sans_filtre_les_cinq_sont_la(self):
        page = self.client.get("/").context["page"]
        self.assertEqual(len(page), 5)

    def test_le_secteur_autre_n_est_pas_propose(self):
        """Une offre "autre" n'est jamais pertinente : l'exposer au filtre
        ferait croire a une categorie consultable."""
        page = self.client.get("/").content.decode("utf-8")
        self.assertIn('value="informatique"', page)
        self.assertNotIn('value="autre"', page)

    def test_un_secteur_inconnu_ne_filtre_rien(self):
        page = self.client.get("/?secteur=peche-a-la-ligne").context["page"]
        self.assertEqual(len(page), 5)

    def test_les_compteurs_suivent_les_secteurs(self):
        compte = self.client.get("/").context["compte"]
        for code in ("informatique", "construction", "agriculture",
                     "eau", "environnement"):
            with self.subTest(secteur=code):
                self.assertEqual(compte[code], 1)

    def test_les_secteurs_sont_declares_une_seule_fois(self):
        """Le filtre, les compteurs et le gabarit lisent la meme liste.

        En dupliquer une seconde ferait qu'un sixieme secteur apparaitrait
        dans le selecteur sans compteur, ou l'inverse.
        """
        from apps.offres.views_web import SECTEURS, SECTEURS_SUIVIS
        reponse = self.client.get("/")
        self.assertEqual([c for c, _ in SECTEURS], SECTEURS_SUIVIS)
        self.assertEqual([c for c, _, _ in reponse.context["compteurs"]],
                         SECTEURS_SUIVIS)
        for code, libelle in SECTEURS:
            with self.subTest(secteur=code):
                self.assertContains(reponse, f'value="{code}"')

    def test_la_colonne_secteur_apparait(self):
        page = self.client.get("/").content.decode("utf-8")
        self.assertIn("Secteur", page)
        self.assertIn("sect-construction", page)
