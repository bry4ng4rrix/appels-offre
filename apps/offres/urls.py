"""Routes de l'application : interface web (session), API privee (jeton),
API publique (lecture seule, sans authentification).

Ordre important : <path:> accepte les barres obliques, donc les routes a
suffixe ("offre/<id>/decider/") doivent preceder la fiche ("offre/<id>/").
"""

from django.urls import path

from . import views_api, views_public, views_web

urlpatterns = [
    # Interface web : authentification par SESSION, comme l'admin.
    path("", views_web.liste, name="web-liste"),
    # AVANT la fiche : <path:> accepte les barres obliques, donc
    # "offre/<path:offre_id>/" avalerait "offre/xxx/decider/" en prenant
    # "xxx/decider" pour un identifiant. Le plus specifique passe d abord.
    path("offre/<path:offre_id>/decider/", views_web.decider,
         name="web-decider"),
    path("offre/<path:offre_id>/dater/", views_web.dater, name="web-dater"),
    path("offre/<path:offre_id>/", views_web.detail, name="web-detail"),
    path("carte/", views_web.carte, name="web-carte"),
    path("suivi/", views_web.suivi, name="web-suivi"),
    path("a-dater/", views_web.a_dater, name="web-a-dater"),
    path("a-dater/banque-mondiale/", views_web.a_dater_banque_mondiale,
         name="web-a-dater-bm"),
    path("carte/points/", views_web.carte_points, name="web-carte-points"),

    # Actions de l'en-tete (HTMX)
    path("actions/veille/", views_web.action_veille, name="web-action-veille"),
    path("actions/trier/", views_web.action_trier, name="web-action-trier"),
    path("actions/verifier-liens/", views_web.action_verifier_liens, name="web-action-liens"),
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
