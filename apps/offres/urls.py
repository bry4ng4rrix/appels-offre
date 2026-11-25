"""Routes de l'application : interface web (session), API privee (jeton),
API publique (lecture seule, sans authentification).

Ordre important : <path:> accepte les barres obliques, donc les routes a
suffixe ("offre/<id>/decider/") doivent preceder la fiche ("offre/<id>/").
"""

from django.urls import path
from django.views.generic import RedirectView

from . import views_api, views_profil, views_public, views_web

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
