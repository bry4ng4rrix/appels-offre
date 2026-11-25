"""Socle Django REST Framework de l'API applicative /api/v1/ (Next.js, Flutter).

Branche dans settings.REST_FRAMEWORK :
  - authentification : X-Session-Token d'allauth headless (applis), puis le
    cookie de session (navigateur, CSRF exige a l'ecriture par DRF) ;
  - droits : connecte par defaut ; `EstAdmin` pour /api/v1/admin/ ;
  - debit : par utilisateur, par adresse anonyme, et par portee (`throttle_scope`) ;
  - pagination et erreurs au format deja publie : {"total", "page", "pages",
    "par_page", "resultats"} et {"erreur", "champs"}.
"""

from allauth.headless.contrib.rest_framework.authentication import XSessionTokenAuthentication
from django.conf import settings
from django.http import Http404
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import exceptions, pagination, permissions, status
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response

from .comptes import est_admin


class JetonSession(XSessionTokenAuthentication):
    """X-Session-Token rendu par /_allauth/app/v1/auth/login. Un jeton faux ou
    expire est refuse (401) au lieu d'etre ignore : l'appli doit le savoir pour
    renvoyer a la connexion. Sans en-tete, la main passe au cookie de session."""

    allow_anonymous_users = False
    allow_invalid_session_tokens = False

    def authenticate(self, request):
        resultat = super().authenticate(request)
        if resultat and not resultat[0].is_active:
            raise exceptions.AuthenticationFailed("Compte désactivé.")
        return resultat

    def authenticate_header(self, request):
        # Present : DRF repond 401 (et non 403) a une requete sans connexion.
        return "X-Session-Token"


class JetonSessionSchema(OpenApiAuthenticationExtension):
    """Decrit l'en-tete dans le schema OpenAPI : les clients generes l'envoient seuls."""

    target_class = "apps.offres.api_drf.JetonSession"
    name = "jetonSession"

    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "header", "name": "X-Session-Token",
                "description": "meta.session_token de POST /_allauth/app/v1/auth/login"}


class EstAdmin(permissions.BasePermission):
    message = "Réservé aux administrateurs."

    def has_permission(self, request, view):
        return est_admin(request.user)


class ContratLisible(permissions.BasePermission):
    """Le schema OpenAPI liste aussi les routes admin : ouvert en developpement,
    reserve aux admins en production. Lu a chaque requete, pas au demarrage."""

    def has_permission(self, request, view):
        return settings.DEBUG or est_admin(request.user)


class Refus(exceptions.APIException):
    """Une regle metier refuse la demande (ValueError d'operations.py)."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "refus"

    def __init__(self, message, statut=None):
        super().__init__(message)
        if statut:
            self.status_code = statut


def appliquer(fonction, *args, statut=None):
    """Appelle une operation partagee ; son ValueError devient une reponse d'erreur."""
    try:
        return fonction(*args)
    except ValueError as exc:
        raise Refus(str(exc), statut)


class Pages(pagination.PageNumberPagination):
    page_size = 27  # comme l'ecran (views_web.PAR_PAGE) : la grille de 3 tombe juste
    page_size_query_param = "par_page"
    max_page_size = 100
    #: Champs ajoutes par la vue a cote des resultats (filtres actifs, seuil...).
    extra: dict = {}

    def get_paginated_response(self, data):
        return Response({"total": self.page.paginator.count, "page": self.page.number,
                         "pages": self.page.paginator.num_pages,
                         "par_page": self.page.paginator.per_page, **self.extra, "resultats": data})

    def get_paginated_response_schema(self, schema):
        return {"type": "object", "required": ["total", "page", "pages", "par_page", "resultats"],
                "properties": {"total": {"type": "integer"}, "page": {"type": "integer"},
                               "pages": {"type": "integer"}, "par_page": {"type": "integer"},
                               "resultats": schema}}


def paginer(requete, lot, serialiseur, taille=None, preparer=None, **extra):
    """Une page de `lot` ; `preparer` s'applique aux seuls elements de la page (annotations)."""
    pages = Pages()
    if taille:
        pages.page_size = taille
    pages.extra = extra
    page = pages.paginate_queryset(lot, requete)
    if preparer:
        page = [preparer(o) for o in page]
    return pages.get_paginated_response(
        serialiseur(page, many=True, context={"request": requete}).data)


class Binaire(BaseRenderer):
    """Laisse passer un fichier (CV, photo, export) quel que soit l'en-tete Accept."""

    media_type = "*/*"
    format = "fichier"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


def erreurs(exc, context):
    """Toutes les erreurs au format {"erreur": "...", "champs": {...}} de l'API."""
    # Import ici : DRF charge ce module (authentification) pendant l'import de ses vues.
    from rest_framework.views import exception_handler
    if isinstance(exc, Http404):
        exc = exceptions.NotFound("Introuvable.")
    reponse = exception_handler(exc, context)
    if reponse is None:
        return None
    donnees = reponse.data
    if isinstance(exc, exceptions.ValidationError):
        champs = donnees if isinstance(donnees, dict) else {"non_field_errors": donnees}
        generales = champs.get("non_field_errors") or []
        reponse.data = {"erreur": str(generales[0]) if generales else "Données invalides.",
                        "champs": champs}
    else:
        detail = donnees.get("detail", donnees) if isinstance(donnees, dict) else donnees
        reponse.data = {"erreur": str(detail)}
    return reponse
