"""Routes de l'application : interface web (session), API privee (jeton),
API publique (lecture seule, sans authentification).

Ordre important : <path:> accepte les barres obliques, donc les routes a
suffixe ("offre/<id>/decider/") doivent preceder la fiche ("offre/<id>/").
"""

from django.urls import path, register_converter
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views_api, views_app, views_profil, views_public, views_web


class Catalogue:
    """« secteurs » ou « pays » : tout autre segment ne correspond a aucune route (404)."""
    regex = "secteurs|pays"

    def to_python(self, valeur):
        return valeur

    def to_url(self, valeur):
        return valeur


register_converter(Catalogue, "catalogue")

urlpatterns = [
    # Interface web : authentification par SESSION, comme l'admin.
    # Accueil : la vitrine publique, sans connexion. La liste complete vit sous /offres/.
    path("", views_public.vitrine, name="public-vitrine"),
    path("offres/", views_web.liste, name="web-liste"),
    path("robots.txt", views_public.robots, name="public-robots"),
    path("sitemap.xml", views_public.sitemap, name="public-sitemap"),
    path("llms.txt", views_public.llms, name="public-llms"),
    # AVANT la fiche : <path:> accepte les barres obliques, donc
    # "offre/<path:offre_id>/" avalerait "offre/xxx/decider/" en prenant
    # "xxx/decider" pour un identifiant. Le plus specifique passe d abord.
    path("offre/<path:offre_id>/decider/", views_web.decider,
         name="web-decider"),
    path("offre/<path:offre_id>/consulter/", views_web.consulter, name="web-consulter"),
    path("offre/<path:offre_id>/dater/", views_web.dater, name="web-dater"),
    path("offre/<path:offre_id>/", views_web.detail, name="web-detail"),
    path("carte/", views_web.carte, name="web-carte"),
    # Anciennes pages retirées de l'interface ; les anciens favoris reviennent
    # vers la liste plutôt que d'afficher une erreur.
    path("suivi/", RedirectView.as_view(pattern_name="web-liste"), name="web-suivi"),
    path("a-dater/", RedirectView.as_view(pattern_name="web-liste"), name="web-a-dater"),
    path("a-dater/banque-mondiale/",
         RedirectView.as_view(pattern_name="web-liste"), name="web-a-dater-bm"),
    path("carte/points/", views_web.carte_points, name="web-carte-points"),

    # Actions de l'en-tete (HTMX)
    path("actions/lancer/<slug:nom>/", views_web.lancer_tache, name="web-lancer"),
    path("actions/etat/", views_web.etat_taches, name="web-etat-taches"),
    path("actions/tache/<int:tache_id>/<slug:action>/", views_web.action_tache,
         name="web-action-tache"),
    path("actions/global/<slug:action>/", views_web.action_globale, name="web-action-globale"),
    path("taches/", views_web.taches, name="web-taches"),
    path("parametres/", views_web.parametres, name="web-parametres"),
    path("parametres/pertinence/", views_web.parametres_pertinence, name="web-parametres-pertinence"),
    path("profil/", views_profil.profil, name="web-profil"),
    path("profil/cv/<int:user_id>/", views_profil.cv, name="web-profil-cv"),
    path("profil/photo/<int:user_id>/", views_profil.photo, name="web-profil-photo"),
    path("pour-vous/", views_profil.pour_vous, name="web-pour-vous"),
    path("notifications/", views_profil.mes_notifications, name="web-notifications"),
    path("abonnement/", views_profil.abonnement, name="web-abonnement"),
    path("abonnements/", views_profil.abonnements_admin, name="web-abonnements"),
    path("abonnements/<int:abonnement_id>/<slug:action>/", views_profil.decider_abonnement,
         name="web-abonnement-decider"),
    path("abonnements/plans/nouveau/", views_profil.enregistrer_plan, name="web-plan-creer"),
    path("abonnements/plans/<int:plan_id>/", views_profil.enregistrer_plan, name="web-plan-modifier"),
    path("guide/vu/", views_profil.guide_vu, name="web-guide-vu"),
    path("parametres/email/", views_web.parametres_email, name="web-parametres-email"),
    path("parametres/email/tester/", views_web.tester_email, name="web-email-tester"),
    path("parametres/secteurs/creer/", views_web.creer_secteur,
         name="web-secteur-creer"),
    path("parametres/secteurs/<int:secteur_id>/modifier/", views_web.modifier_secteur,
         name="web-secteur-modifier"),
    path("parametres/secteurs/<int:secteur_id>/basculer/", views_web.basculer_secteur,
         name="web-secteur-basculer"),
    path("parametres/secteurs/<int:secteur_id>/supprimer/", views_web.supprimer_secteur,
         name="web-secteur-supprimer"),
    path("parametres/pays/creer/", views_web.creer_pays, name="web-pays-creer"),
    path("parametres/pays/<int:pays_id>/modifier/", views_web.modifier_pays,
         name="web-pays-modifier"),
    path("parametres/pays/<int:pays_id>/basculer/", views_web.basculer_pays,
         name="web-pays-basculer"),
    path("parametres/pays/<int:pays_id>/supprimer/", views_web.supprimer_pays,
         name="web-pays-supprimer"),
    path("taches/cles/creer/", views_web.creer_cle_api, name="web-cle-creer"),
    path("taches/cles/<int:cle_id>/revoquer/", views_web.revoquer_cle_api, name="web-cle-revoquer"),
    path("exporter/", views_web.exporter, name="web-exporter"),
    path("recapitulatif/", views_web.recapitulatif, name="web-recapitulatif"),

    # API : authentification par JETON. Les deux regimes sont volontairement
    # distincts, et servis par deux modules de vues separes. Lecture en GET,
    # decisions en POST -- voir l'en-tete de offres/views_api.py.
    path("api/offres/", views_api.liste, name="offres-liste"),
    path("api/statistiques/", views_api.statistiques, name="statistiques"),
    path("api/sources/", views_api.sources, name="api-sources"),
    path("api/secteurs/", views_api.secteurs, name="api-secteurs"),
    path("api/regions/", views_api.liste_regions, name="api-regions"),
    path("api/carte/points/", views_api.carte_points, name="api-carte-points"),
    path("api/suivi/", views_api.liste_suivi, name="api-suivi"),
    # Ecriture. Meme regle d'ordre que pour l'interface : les routes a
    # suffixe passent avant la fiche, dont <path:> avalerait le suffixe.
    path("api/offres/<path:offre_id>/decision/", views_api.decision, name="api-decision"),
    path("api/offres/<path:offre_id>/echeance/", views_api.echeance, name="api-echeance"),
    path("api/offres/<path:offre_id>/verdict/", views_api.verdict, name="api-verdict"),
    path("api/offres/<path:offre_id>/", views_api.detail, name="offres-detail"),

    # API APPLICATIVE des frontends (Next.js, Flutter), en Django REST Framework :
    # connexion par allauth headless (/_allauth/), puis X-Session-Token.
    # Contrat : /api/v1/schema/ (OpenAPI), lisible dans /api/v1/docs/. Voir views_app.py.
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="api-v1-schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="api-v1-schema"), name="api-v1-docs"),
    path("api/v1/reference/", views_app.reference, name="api-v1-reference"),
    path("api/v1/plans/", views_app.plans, name="api-v1-plans"),
    path("api/v1/moi/", views_app.moi, name="api-v1-moi"),
    path("api/v1/offres/", views_app.offres, name="api-v1-offres"),
    path("api/v1/offres/<path:offre_id>/consulter/", views_app.consulter, name="api-v1-consulter"),
    path("api/v1/offres/<path:offre_id>/", views_app.offre, name="api-v1-offre"),
    path("api/v1/carte/points/", views_app.carte_points, name="api-v1-carte-points"),
    path("api/v1/pour-vous/", views_app.pour_vous, name="api-v1-pour-vous"),
    path("api/v1/profil/", views_app.profil, name="api-v1-profil"),
    path("api/v1/profil/perso/", views_app.profil_perso, name="api-v1-profil-perso"),
    path("api/v1/profil/pro/", views_app.profil_pro, name="api-v1-profil-pro"),
    path("api/v1/profil/domaines/", views_app.profil_domaines, name="api-v1-profil-domaines"),
    path("api/v1/profil/preferences/", views_app.profil_preferences, name="api-v1-profil-preferences"),
    path("api/v1/profil/cv/", views_app.profil_cv, name="api-v1-profil-cv"),
    path("api/v1/profil/photo/", views_app.profil_photo, name="api-v1-profil-photo"),
    path("api/v1/notifications/", views_app.notifications, name="api-v1-notifications"),
    path("api/v1/abonnements/", views_app.abonnements, name="api-v1-abonnements"),
    # Admin (403 sinon).
    path("api/v1/admin/offres/<path:offre_id>/decision/", views_app.admin_decision,
         name="api-v1-admin-decision"),
    path("api/v1/admin/offres/<path:offre_id>/echeance/", views_app.admin_echeance,
         name="api-v1-admin-echeance"),
    path("api/v1/admin/offres/<path:offre_id>/verdict/", views_app.admin_verdict,
         name="api-v1-admin-verdict"),
    path("api/v1/admin/statistiques/", views_app.admin_statistiques, name="api-v1-admin-statistiques"),
    path("api/v1/admin/sources/", views_app.admin_sources, name="api-v1-admin-sources"),
    path("api/v1/admin/suivi/", views_app.admin_suivi, name="api-v1-admin-suivi"),
    path("api/v1/admin/exporter/", views_app.admin_exporter, name="api-v1-admin-exporter"),
    path("api/v1/admin/abonnements/", views_app.admin_abonnements, name="api-v1-admin-abonnements"),
    path("api/v1/admin/abonnements/<int:abonnement_id>/valider/", views_app.admin_abonnement_valider,
         name="api-v1-admin-abonnement-valider"),
    path("api/v1/admin/abonnements/<int:abonnement_id>/refuser/", views_app.admin_abonnement_refuser,
         name="api-v1-admin-abonnement-refuser"),
    path("api/v1/admin/plans/", views_app.admin_plans, name="api-v1-admin-plans"),
    path("api/v1/admin/plans/<int:plan_id>/", views_app.admin_plan, name="api-v1-admin-plan"),
    path("api/v1/admin/taches/", views_app.admin_taches, name="api-v1-admin-taches"),
    path("api/v1/admin/taches/lancer/<slug:nom>/", views_app.admin_tache_lancer,
         name="api-v1-admin-tache-lancer"),
    path("api/v1/admin/taches/toutes/<slug:action>/", views_app.admin_taches_toutes,
         name="api-v1-admin-taches-toutes"),
    path("api/v1/admin/taches/<int:tache_id>/", views_app.admin_tache, name="api-v1-admin-tache"),
    path("api/v1/admin/taches/<int:tache_id>/<slug:action>/", views_app.admin_tache_action,
         name="api-v1-admin-tache-action"),
    path("api/v1/admin/parametres/", views_app.admin_parametres, name="api-v1-admin-parametres"),
    path("api/v1/admin/parametres/collecte/", views_app.admin_parametres_collecte,
         name="api-v1-admin-parametres-collecte"),
    path("api/v1/admin/parametres/email/", views_app.admin_parametres_email,
         name="api-v1-admin-parametres-email"),
    path("api/v1/admin/parametres/email/tester/", views_app.admin_parametres_email_tester,
         name="api-v1-admin-parametres-email-tester"),
    path("api/v1/admin/parametres/pertinence/", views_app.admin_parametres_pertinence,
         name="api-v1-admin-parametres-pertinence"),
    path("api/v1/admin/<catalogue:catalogue>/", views_app.admin_catalogue, name="api-v1-admin-catalogue"),
    path("api/v1/admin/<catalogue:catalogue>/<int:objet_id>/", views_app.admin_catalogue_element,
         name="api-v1-admin-catalogue-element"),
    path("api/v1/admin/<catalogue:catalogue>/<int:objet_id>/basculer/", views_app.admin_catalogue_basculer,
         name="api-v1-admin-catalogue-basculer"),
    path("api/v1/admin/cles/", views_app.admin_cles, name="api-v1-admin-cles"),
    path("api/v1/admin/cles/<int:cle_id>/", views_app.admin_cle, name="api-v1-admin-cle"),

    # API PUBLIQUE : aucune authentification, lecture seule, sans le suivi
    # commercial ni les ecartees. Voir offres/views_public.py et, dans
    # settings.py, API_PUBLIQUE_SOURCES_EXCLUES pour le cadre juridique.
    path("api/public/", views_public.index, name="public-index"),
    path("api/public/offres/", views_public.liste, name="public-offres"),
    path("api/public/statistiques/", views_public.statistiques, name="public-statistiques"),
    path("api/public/sources/", views_public.sources, name="public-sources"),
    path("api/public/secteurs/", views_public.secteurs, name="public-secteurs"),
    path("api/public/regions/", views_public.liste_regions, name="public-regions"),
    path("api/public/lieux/", views_public.lieux, name="public-lieux"),
    path("api/public/carte/points/", views_public.carte_points, name="public-carte-points"),
    path("api/public/offres/<path:offre_id>/", views_public.detail, name="public-offre"),
]
