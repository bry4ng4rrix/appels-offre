"""Tests du suivi commercial.

Le suivi est la seule donnee du systeme qu'un humain saisit. Deux choses
doivent tenir : elle survit a un re-tri de l'offre, et elle ne se pose pas
par un simple GET.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.offres.auth import empreinte, engendrer
from apps.offres.models import PRESUMEE_CLOSE_JOURS, CleApi, Offre, Suivi


class SuiviTests(TestCase):
    def setUp(self):
        self.utilisateur = User.objects.create_user("essai", password="essai-mdp-1")
        self.client.force_login(self.utilisateur)
        maintenant = timezone.now()
        self.offre = Offre.objects.create(
            id="essai-1", source="armp", titre="Fourniture de materiels informatiques",
            pertinent=True, nature="marche", secteur="informatique",
            date_ajout=maintenant, date_maj=maintenant)

    def test_une_decision_est_enregistree(self):
        reponse = self.client.post(
            reverse("web-decider", args=[self.offre.pk]),
            {"statut": Suivi.CANDIDATURE, "note": "dossier depose le 4"})
        self.assertEqual(reponse.status_code, 302)
        suivi = Suivi.objects.get(offre_id=self.offre.pk)
        self.assertEqual(suivi.statut, Suivi.CANDIDATURE)
        self.assertEqual(suivi.note, "dossier depose le 4")
        self.assertEqual(suivi.decide_par, self.utilisateur)

    def test_une_seconde_decision_remplace_la_premiere(self):
        url = reverse("web-decider", args=[self.offre.pk])
        self.client.post(url, {"statut": Suivi.A_ETUDIER})
        self.client.post(url, {"statut": Suivi.GAGNE, "note": "signe"})
        self.assertEqual(Suivi.objects.filter(offre_id=self.offre.pk).count(), 1)
        self.assertEqual(Suivi.objects.get(offre_id=self.offre.pk).statut, Suivi.GAGNE)

    def test_un_get_ne_decide_rien(self):
        # Un prechargement de navigateur ou un robot ne doit pas pouvoir
        # changer l'etat commercial d'une offre.
        reponse = self.client.get(reverse("web-decider", args=[self.offre.pk]))
        self.assertEqual(reponse.status_code, 405)
        self.assertFalse(Suivi.objects.exists())

    def test_un_statut_inconnu_est_refuse(self):
        self.client.post(reverse("web-decider", args=[self.offre.pk]),
                         {"statut": "invente"})
        self.assertFalse(Suivi.objects.exists())

    def test_la_route_decider_n_est_pas_avalee_par_la_fiche(self):
        # <path:> accepte les barres obliques : si l'ordre des routes etait
        # inverse, cette URL rendrait la fiche d'une offre "essai-1/decider".
        resolue = reverse("web-decider", args=[self.offre.pk])
        self.assertTrue(resolue.endswith("/decider/"))
        self.assertEqual(self.client.get(resolue).status_code, 405)

    def test_le_suivi_survit_a_un_re_tri_de_l_offre(self):
        # db.enregistrer reecrit la ligne d'offres a chaque re-tri. Le suivi
        # vit dans une autre table, precisement pour ne pas etre efface.
        self.client.post(reverse("web-decider", args=[self.offre.pk]),
                         {"statut": Suivi.CANDIDATURE})
        Offre.objects.filter(pk=self.offre.pk).update(
            pertinent=False, secteur="autre", categorie="Non pertinent")
        self.assertEqual(Suivi.objects.get(offre_id=self.offre.pk).statut,
                         Suivi.CANDIDATURE)

    def test_l_entonnoir_compte_les_etapes(self):
        maintenant = timezone.now()
        for i, statut in enumerate([Suivi.A_ETUDIER, Suivi.CANDIDATURE,
                                    Suivi.GAGNE, Suivi.PERDU, Suivi.HORS_SUJET]):
            offre = Offre.objects.create(
                id=f"essai-lot-{i}", source="armp", titre=f"Offre {i}",
                pertinent=True, date_ajout=maintenant, date_maj=maintenant)
            Suivi.objects.create(offre=offre, statut=statut)
        reponse = self.client.get(reverse("web-suivi"))
        self.assertEqual(reponse.status_code, 200)
        entonnoir = dict((libelle, n) for libelle, n, _ in
                         reponse.context["entonnoir"])
        # Deposees = candidature + gagne + perdu.
        self.assertEqual(entonnoir["Candidatures déposées"], 3)
        self.assertEqual(entonnoir["Gagnées"], 1)
        self.assertEqual(reponse.context["hors_sujet"], 1)

    def test_la_page_est_fermee_aux_anonymes(self):
        self.client.logout()
        reponse = self.client.get(reverse("web-suivi"))
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("/comptes/login/", reponse["Location"])


class PresomptionClotureTests(TestCase):
    """Une offre sans echeance ne doit pas rester "actionnable" pour toujours.

    67 % des offres actionnables n'avaient aucune date limite, dont 546 pour
    la seule BAD, qui ne publie pas ses dates de depot. Le compteur affichait
    donc majoritairement des avis perimes.
    """

    def setUp(self):
        self.utilisateur = User.objects.create_user("essai2", password="essai-mdp-2")
        self.client.force_login(self.utilisateur)
        maintenant = timezone.now()

        def offre(cle, date_limite, age_jours, publication=None):
            Offre.objects.create(
                id=cle, source="bad", titre=f"Offre {cle}", pertinent=True,
                nature="marche", secteur="informatique", date_limite=date_limite,
                date_publication=publication)
            # date_ajout est auto_now_add : on la recule apres coup.
            Offre.objects.filter(pk=cle).update(date_ajout=maintenant - timedelta(days=age_jours))
            return Offre.objects.get(pk=cle)

        self.recente = offre("sans-date-recente", None, 3)
        self.ancienne = offre("sans-date-ancienne", None, PRESUMEE_CLOSE_JOURS + 5)
        self.datee = offre("datee-ouverte",
                           (maintenant + timedelta(days=10)).date(), 60)
        # Le cas qui a motive tout ceci : collectee hier, publiee il y a des
        # mois. Les 546 avis BAD sont dans cette situation -- tous collectes
        # le 21 aout, publies jusqu'a 146 jours plus tot.
        self.vieille_publication = offre(
            "publiee-il-y-a-longtemps", None, 1,
            publication=(maintenant - timedelta(days=PRESUMEE_CLOSE_JOURS + 40)).date())
        # Et son inverse : collectee il y a longtemps, publiee recemment.
        self.publication_fraiche = offre(
            "publiee-hier", None, PRESUMEE_CLOSE_JOURS + 10,
            publication=(maintenant - timedelta(days=2)).date())

    def _ids(self, **params):
        reponse = self.client.get(reverse("web-liste"), params)
        return {o.id for o in reponse.context["page"].object_list}

    def test_une_offre_sans_date_recente_reste_actionnable(self):
        assert self.recente.id in self._ids()

    def test_une_offre_sans_date_ancienne_sort_des_actionnables(self):
        assert self.ancienne.id not in self._ids()

    def test_une_offre_datee_et_ouverte_n_est_pas_touchee(self):
        # L'anciennete ne doit jouer QUE sur les offres sans echeance : une
        # offre datee et encore ouverte reste actionnable a tout age.
        assert self.datee.id in self._ids()

    def test_les_presumees_closes_restent_consultables(self):
        # Une presomption n'est pas une certitude : elles ont leur propre vue.
        vues = self._ids(etat="sans-echeance")
        assert self.ancienne.id in vues
        assert self.recente.id not in vues

    def test_la_date_de_publication_prime_sur_celle_de_la_collecte(self):
        """Le defaut que la presomption devait corriger.

        Une offre collectee hier mais publiee il y a trois mois est close.
        Se fier a date_ajout la faisait passer pour fraiche : c'est ce qui
        laissait 477 avis BAD perimes dans les actionnables.
        """
        assert self.vieille_publication.id not in self._ids()
        assert self.vieille_publication.id in self._ids(etat="sans-echeance")

    def test_une_publication_recente_sauve_une_collecte_ancienne(self):
        # L'inverse doit valoir aussi : la collecte ancienne ne condamne pas
        # une offre que la source vient de publier.
        assert self.publication_fraiche.id in self._ids()

    def test_l_ecran_dit_pourquoi_et_depuis_quand(self):
        reponse = self.client.get(reverse("web-detail", args=[self.ancienne.id]))
        assert reponse.context["offre"].etat_echeance == "presumee"
        assert reponse.context["offre"].jours >= PRESUMEE_CLOSE_JOURS

    def test_l_api_applique_la_meme_regle_que_l_ecran(self):
        """Sans cela, n8n et le site public proposeraient des offres que
        l'interface ne montre plus -- une divergence invisible et durable."""
        jeton = engendrer()
        CleApi.objects.create(nom="essai presomption", empreinte=empreinte(jeton))
        reponse = self.client.get(reverse("offres-liste"),
                                  HTTP_AUTHORIZATION=f"Bearer {jeton}")
        self.assertEqual(reponse.status_code, 200)
        rendus = {o["id"] for o in reponse.json()["offres"]}
        assert self.recente.id in rendus
        assert self.datee.id in rendus
        assert self.ancienne.id not in rendus

    def test_l_api_les_rend_si_on_demande_les_cloturees(self):
        jeton = engendrer()
        CleApi.objects.create(nom="essai cloturees", empreinte=empreinte(jeton))
        reponse = self.client.get(reverse("offres-liste"), {"cloturees": "1"},
                                  HTTP_AUTHORIZATION=f"Bearer {jeton}")
        rendus = {o["id"] for o in reponse.json()["offres"]}
        assert self.ancienne.id in rendus


class LienRetireTests(TestCase):
    """Une offre que sa source a retiree n'est plus actionnable.

    Constate, pas deduit : c'est verifier_liens.py qui ouvre le lien et lit
    la page. "illisible" ne ferme rien -- un 403 ou une panne du site ne
    prouvent pas qu'une offre est close.
    """

    def setUp(self):
        self.utilisateur = User.objects.create_user("essai3", password="essai-mdp-3")
        self.client.force_login(self.utilisateur)
        maintenant = timezone.now()
        demain = (maintenant + timedelta(days=20)).date()

        def offre(cle, etat):
            return Offre.objects.create(
                id=cle, source="unjobnet", titre=f"Offre {cle}", pertinent=True,
                nature="marche", secteur="informatique", date_limite=demain,
                lien=f"https://exemple.invalid/{cle}", lien_etat=etat,
                lien_verifie_le=maintenant,
                date_ajout=maintenant, date_maj=maintenant)

        self.en_ligne = offre("lien-ouverte", "ouverte")
        self.disparue = offre("lien-introuvable", "introuvable")
        self.annoncee = offre("lien-close", "close")
        self.illisible = offre("lien-illisible", "illisible")
        self.jamais_vue = offre("lien-jamais-verifie", None)

    def _ids(self, **params):
        reponse = self.client.get(reverse("web-liste"), params)
        return {o.id for o in reponse.context["page"].object_list}

    def test_une_offre_retiree_sort_des_actionnables(self):
        actionnables = self._ids()
        assert self.disparue.id not in actionnables
        assert self.annoncee.id not in actionnables

    def test_une_offre_en_ligne_ou_jamais_verifiee_reste_actionnable(self):
        actionnables = self._ids()
        assert self.en_ligne.id in actionnables
        assert self.jamais_vue.id in actionnables

    def test_une_page_illisible_ne_ferme_rien(self):
        # Le point le plus important : un site qui refuse ou tombe ne doit
        # pas faire disparaitre des offres valides.
        assert self.illisible.id in self._ids()

    def test_les_retirees_restent_consultables(self):
        retirees = self._ids(etat="retirees")
        assert self.disparue.id in retirees
        assert self.annoncee.id in retirees
        assert self.en_ligne.id not in retirees

    def test_l_api_ne_propose_pas_une_offre_retiree(self):
        jeton = engendrer()
        CleApi.objects.create(nom="essai lien", empreinte=empreinte(jeton))
        reponse = self.client.get(reverse("offres-liste"),
                                  HTTP_AUTHORIZATION=f"Bearer {jeton}")
        rendus = {o["id"] for o in reponse.json()["offres"]}
        assert self.en_ligne.id in rendus
        assert self.illisible.id in rendus
        assert self.disparue.id not in rendus
        assert self.annoncee.id not in rendus


class EcheanceManuelleTests(TestCase):
    """Une echeance saisie a la main doit survivre au pipeline.

    C'est toute la raison d'etre de sa double ecriture : suivi.echeance
    garde la trace humaine, offres.date_limite sert aux vues -- et
    db.enregistrer ne peut plus blanchir cette derniere.
    """

    def setUp(self):
        self.utilisateur = User.objects.create_user("essai4", password="essai-mdp-4")
        self.client.force_login(self.utilisateur)
        maintenant = timezone.now()
        self.offre = Offre.objects.create(
            id="bad-sans-date", source="bad", titre="AMI - Madagascar - Etude",
            organisation="BAD", pays="Madagascar", pertinent=True,
            nature="marche", secteur="informatique", date_limite=None,
            date_publication=maintenant.date(), lien="https://exemple.invalid/x",
            date_ajout=maintenant, date_maj=maintenant)

    def test_la_saisie_ecrit_aux_deux_endroits(self):
        reponse = self.client.post(reverse("web-dater", args=[self.offre.pk]),
                                   {"echeance": "2026-10-15"})
        self.assertEqual(reponse.status_code, 302)
        self.offre.refresh_from_db()
        self.assertEqual(str(self.offre.date_limite), "2026-10-15")
        suivi = Suivi.objects.get(offre_id=self.offre.pk)
        self.assertEqual(str(suivi.echeance), "2026-10-15")
        self.assertEqual(suivi.decide_par, self.utilisateur)
        self.assertIsNotNone(suivi.echeance_saisie_le)

    def test_une_date_illisible_est_refusee(self):
        self.client.post(reverse("web-dater", args=[self.offre.pk]),
                         {"echeance": "15/10/2026"})
        self.offre.refresh_from_db()
        self.assertIsNone(self.offre.date_limite)
        self.assertFalse(Suivi.objects.filter(offre_id=self.offre.pk).exists())

    def test_un_get_ne_date_rien(self):
        reponse = self.client.get(reverse("web-dater", args=[self.offre.pk]))
        self.assertEqual(reponse.status_code, 405)

    def test_l_offre_quitte_la_file_une_fois_datee(self):
        avant = {o.id for o in self.client.get(reverse("web-a-dater"))
                 .context["page"].object_list}
        assert self.offre.id in avant
        self.client.post(reverse("web-dater", args=[self.offre.pk]),
                         {"echeance": "2026-10-15"})
        apres = {o.id for o in self.client.get(reverse("web-a-dater"))
                 .context["page"].object_list}
        assert self.offre.id not in apres

    def test_une_offre_hors_sujet_quitte_la_file(self):
        # Inutile de dater ce qu'on ne poursuivra pas.
        self.client.post(reverse("web-decider", args=[self.offre.pk]),
                         {"statut": Suivi.HORS_SUJET})
        ids = {o.id for o in self.client.get(reverse("web-a-dater"))
               .context["page"].object_list}
        assert self.offre.id not in ids

    def test_les_projets_banque_mondiale_ne_sont_pas_dans_la_file(self):
        # Ce sont des pages de projet remontant a 1980, sans description :
        # les dater a la main n'aurait aucun sens. Decision de l'exploitant.
        maintenant = timezone.now()
        Offre.objects.create(
            id="bm-projet", source="banquemondiale", titre="LIVESTOCK(DROP)",
            pays="Madagascar", pertinent=True, nature="marche",
            secteur="agriculture", date_ajout=maintenant, date_maj=maintenant)
        ids = {o.id for o in self.client.get(reverse("web-a-dater"))
               .context["page"].object_list}
        assert "bm-projet" not in ids
        assert self.offre.id in ids   # la BAD, elle, y reste
        # ... et ils ont leur propre page, ou la BAD n'est PAS.
        a_part = {o.id for o in self.client.get(reverse("web-a-dater-bm"))
                  .context["page"].object_list}
        assert "bm-projet" in a_part
        assert self.offre.id not in a_part

    def test_madagascar_passe_en_tete_de_file(self):
        maintenant = timezone.now()
        Offre.objects.create(
            id="bad-ailleurs", source="bad", titre="AMI - Niger - Etude",
            pays="Niger", pertinent=True, nature="marche", secteur="informatique",
            date_publication=maintenant.date(),
            date_ajout=maintenant, date_maj=maintenant)
        ordre = [o.id for o in self.client.get(reverse("web-a-dater"))
                 .context["page"].object_list]
        assert ordre.index("bad-sans-date") < ordre.index("bad-ailleurs")
