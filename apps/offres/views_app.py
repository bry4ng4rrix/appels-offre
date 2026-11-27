"""API applicative /api/v1/ pour les frontends Next.js et Flutter (Django REST Framework).

Connexion : django-allauth headless, sous /_allauth/app/v1/ (spec : /_allauth/openapi.html).
La connexion rend `meta.session_token`, a presenter ensuite dans l'en-tete
X-Session-Token. Un navigateur peut aussi utiliser /_allauth/browser/v1/ et le
cookie de session, avec l'en-tete X-CSRFToken pour ecrire.

Contrat exact : /api/v1/schema/ (OpenAPI 3), lisible dans /api/v1/docs/. Les
clients TypeScript et Dart s'en generent (voir docs/API.md). Socle commun
(authentification, droits, debit, pagination, erreurs) : api_drf.py. Formes des
donnees : serializers.py. Aucune regle metier ici : filtres et echeances
(views_web), credits (models.Consultation), profil (forms), administration
(operations). Cette couche traduit en HTTP, rien de plus.
"""

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers as champs
from rest_framework import status
from rest_framework.decorators import (api_view, parser_classes, permission_classes,
                                       renderer_classes, throttle_classes)
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from . import operations
from . import serializers as s
from .api_drf import Binaire, EstAdmin, Refus, appliquer, paginer
from .comptes import est_admin
from .models import (Abonnement, Categorie, CleApi, Consultation, Inscription, Notification, Offre,
                     Parametres, Pays, Plan, Preferences, Profil, Secteur, Suivi, Tache)
from .scrapers import REGISTRE_SCRAPERS
from .services import geo
from .services.correspondance import suggestions
from .views_api import donnees_sources, donnees_statistiques
from .views_profil import _resume, deposer_cv, demander_plan, supprimer_cv
from .views_web import (CREDITS_EPUISES, _contexte_parametres, _contexte_pays,
                        _contexte_pertinence, _contexte_secteurs, _contexte_sources,
                        agreger_par_lieu, annoter, filtrer, libelles_secteurs, pays_disponibles,
                        secteurs_disponibles)

#: Les onglets de la liste (parametre ?etat=), dans l'ordre de l'ecran.
ETATS = [("toutes", "Ouvertes"), ("actionnables", "Actionnables"), ("retenues", "Retenues"),
         ("sans-echeance", "Sans échéance"), ("cloturees", "Clôturées"),
         ("retirees", "Retirées"), ("ecartees", "Écartées")]

ADMIN = [IsAuthenticated, EstAdmin]
ERREURS = {400: s.ErreurSerializer, 401: s.ErreurSerializer, 403: s.ErreurSerializer,
           404: s.ErreurSerializer, 429: s.ErreurSerializer}


class ConsulterThrottle(UserRateThrottle):
    """Ouvrir des annonces en rafale : un robot, pas une personne (DEFAULT_THROTTLE_RATES)."""
    scope = "consulter"


class TeleversementThrottle(UserRateThrottle):
    scope = "televersement"


def _annoteur():
    aujourdhui, libelles = timezone.now().date(), libelles_secteurs()
    return lambda offre: annoter(offre, aujourdhui, libelles)


def _saisie(serialiseur, request):
    saisie = serialiseur(data=request.data)
    saisie.is_valid(raise_exception=True)
    return saisie.validated_data


def _chemin(nom, valeurs):
    return OpenApiParameter(nom, str, OpenApiParameter.PATH, enum=list(valeurs))


PARAMETRES_LISTE = [
    OpenApiParameter("etat", str, enum=[c for c, _ in ETATS], description="Onglet (défaut : toutes = ouvertes)."),
    OpenApiParameter("q", str, description="Titre, organisation ou catégorie."),
    OpenApiParameter("secteur", str, description="Code de /reference/ secteurs."),
    OpenApiParameter("pays", str, description="Code de /reference/ pays."),
    OpenApiParameter("region", str, enum=[c for c, _ in geo.LIBELLES]),
    OpenApiParameter("lieu", str, description="Lieu exact, tel que la carte le donne."),
    OpenApiParameter("nature", str, enum=["marche", "emploi", "inconnue"]),
    OpenApiParameter("date_de", OpenApiTypes.DATE, description="Échéance à partir de."),
    OpenApiParameter("date_a", OpenApiTypes.DATE, description="Échéance jusqu'à."),
]
PAGINATION = [OpenApiParameter("page", int), OpenApiParameter("par_page", int, description="100 au plus.")]

PageOffres = s.page_de(s.OffreSerializer, "PageOffres")
PageSuggestions = s.page_de(s.SuggestionSerializer, "PageSuggestions",
                            profil_vide=champs.BooleanField(), seuil=champs.IntegerField(),
                            completion=champs.IntegerField(), resume=s.ResumeSerializer(many=True))
PageNotifications = s.page_de(s.NotificationSerializer, "PageNotifications",
                              alertes_actives=champs.BooleanField())
PageAbonnements = s.page_de(s.AbonnementAdminSerializer, "PageAbonnementsAdmin",
                            en_attente=champs.IntegerField())
PageSuivi = s.page_de(s.SuiviLigneSerializer, "PageSuivi")


# ------------------------------------------------------------------ public

@extend_schema(tags=["public"], responses=s.ReferenceSerializer)
@api_view(["GET"])
@permission_classes([AllowAny])
def reference(request):
    """GET /api/v1/reference/ — les listes de choix (filtres, formulaires du profil)."""
    return Response(s.ReferenceSerializer({
        "etats": s.choix(ETATS), "natures": s.choix(Offre.NATURE_CHOICES),
        "secteurs": s.choix(secteurs_disponibles()), "pays": s.choix(pays_disponibles()),
        "regions": s.choix(geo.LIBELLES), "statuts_suivi": s.choix(Suivi.STATUT_CHOICES),
        "profil": {
            "secteurs": Secteur.objects.filter(actif=True).values("id", "nom"),
            "categories": Categorie.objects.filter(actif=True).values("id", "nom"),
            "pays": Pays.objects.filter(actif=True).values("id", "nom"),
            "regions": s.choix(c for c in geo.LIBELLES if c[0] != geo.INCONNUE),
            "types_offres": s.choix(Preferences.TYPES), "niveaux_etudes": s.choix(Profil.NIVEAUX),
            "types_contrat": s.choix(Profil.CONTRATS), "disponibilites": s.choix(Profil.DISPONIBILITES),
            "modes_travail": s.choix(Profil.MODES),
        },
        "essai_jours": Inscription.ESSAI_JOURS,
    }).data)


@extend_schema(tags=["public"], responses=s.PlanSerializer(many=True))
@api_view(["GET"])
@permission_classes([AllowAny])
def plans(request):
    """GET /api/v1/plans/ — les plans d'abonnement proposés."""
    return Response(s.PlanSerializer(Plan.objects.filter(actif=True), many=True).data)


# ---------------------------------------------------------------- compte

def _avatar(user, fiche) -> str | None:
    if fiche.photo:
        return reverse("api-v1-profil-photo")
    compte = user.socialaccount_set.first()
    return compte.get_avatar_url() if compte else None


@extend_schema(tags=["compte"], responses={200: s.MoiSerializer, **ERREURS})
@api_view(["GET"])
def moi(request):
    """GET /api/v1/moi/ — le compte connecté, son rôle et ses crédits."""
    user, fiche = request.user, Profil.de(request.user)
    return Response(s.MoiSerializer({
        "id": user.pk, "email": user.email, "prenom": user.first_name, "nom": user.last_name,
        "admin": est_admin(user), "avatar": _avatar(user, fiche), "completion": fiche.completion(),
        "credits": s.credits(user)}).data)


# ------------------------------------------------------------------ offres

@extend_schema(tags=["offres"], operation_id="offres_liste", parameters=PARAMETRES_LISTE + PAGINATION,
               responses=PageOffres)
@api_view(["GET"])
def offres(request):
    """GET /api/v1/offres/ — la liste filtrée, échéance la plus proche d'abord."""
    lot, _ = filtrer(request)
    return paginer(request, lot.order_by("date_limite", "-date_ajout"), s.OffreSerializer,
                   preparer=_annoteur())


@extend_schema(tags=["offres"], operation_id="offres_detail", responses={200: s.OffreDetailSerializer, **ERREURS})
@api_view(["GET"])
def offre(request, offre_id):
    """GET /api/v1/offres/<id>/ — la fiche, et les offres voisines de la même source."""
    fiche = annoter(get_object_or_404(Offre, pk=offre_id), libelles=libelles_secteurs())
    fiche.voisines = (Offre.objects.filter(source=fiche.source, pertinent=True)
                      .exclude(pk=fiche.pk).order_by("date_limite")[:5])
    fiche.deja_consultee = Consultation.objects.filter(
        user=request.user, offre=fiche, jour=timezone.localdate()).exists()
    fiche.suivi_api = Suivi.objects.filter(offre_id=fiche.pk).first()
    return Response(s.OffreDetailSerializer(fiche, context={"request": request}).data)


@extend_schema(tags=["offres"], request=None, responses={
    200: s.ConsulterSerializer,
    402: OpenApiResponse(s.CreditsEpuisesSerializer, description="Plus de crédits : proposer un plan."),
    **ERREURS})
@api_view(["POST"])
@throttle_classes([UserRateThrottle, ConsulterThrottle])
def consulter(request, offre_id):
    """POST /api/v1/offres/<id>/consulter/ — le lien officiel, contre un crédit (gratuit si déjà ouverte aujourd'hui)."""
    fiche = get_object_or_404(Offre, pk=offre_id)
    if not fiche.lien:
        raise Refus("Cette offre n'a pas d'annonce officielle.", status.HTTP_404_NOT_FOUND)
    user = request.user
    if not est_admin(user) and not Consultation.debiter_verrouille(user, fiche):
        return Response({"erreur": CREDITS_EPUISES, "code": "credits_epuises",
                         "credits": s.credits(user)}, status=status.HTTP_402_PAYMENT_REQUIRED)
    return Response({"lien": fiche.lien, "credits": s.credits(user)})


@extend_schema(tags=["offres"], parameters=PARAMETRES_LISTE, responses=s.CarteSerializer)
@api_view(["GET"])
def carte_points(request):
    """GET /api/v1/carte/points/ — les offres regroupées par lieu (mêmes filtres que la liste)."""
    return Response(agreger_par_lieu(filtrer(request)[0]))


@extend_schema(tags=["offres"], parameters=PAGINATION, responses=PageSuggestions)
@api_view(["GET"])
def pour_vous(request):
    """GET /api/v1/pour-vous/ — suggestions selon le profil, meilleur score d'abord."""
    criteres, lot = suggestions(request.user)
    return paginer(request, lot, s.SuggestionSerializer, preparer=_annoteur(),
                   profil_vide=criteres.vide, seuil=criteres.seuil,
                   completion=Profil.de(request.user).completion(),
                   resume=[{"titre": t, "valeurs": v} for t, v in _resume(request.user)])


# ------------------------------------------------------------------ profil

def profil_dict(user) -> dict:
    fiche, prefs = Profil.de(user), Preferences.de(user)
    return {
        "perso": {"first_name": user.first_name, "last_name": user.last_name,
                  "telephone": fiche.telephone, "adresse": fiche.adresse, "ville": fiche.ville,
                  "region": fiche.region, "code_postal": fiche.code_postal, "pays": fiche.pays_id,
                  "date_naissance": fiche.date_naissance},
        "pro": {"titre": fiche.titre, "description": fiche.description,
                "annees_experience": fiche.annees_experience, "niveau_etudes": fiche.niveau_etudes,
                "type_contrat": fiche.type_contrat, "disponibilite": fiche.disponibilite,
                "mode_travail": fiche.mode_travail},
        "domaines": {"secteurs": [x.pk for x in fiche.secteurs.all()],
                     "categories": [x.pk for x in fiche.categories.all()],
                     "competences_texte": ", ".join(c.nom for c in fiche.competences.all()),
                     "mots_cles": fiche.mots_cles},
        "preferences": {"pays": [x.pk for x in prefs.pays.all()], "regions": prefs.regions,
                        "villes": prefs.villes, "types_offres": prefs.types_offres,
                        "teletravail": prefs.teletravail, "seuil": prefs.seuil,
                        "notifications": prefs.notifications},
        "photo": _avatar(user, fiche),
        "cv": {"nom": fiche.cv_nom, "depose_le": fiche.cv_depose_le} if fiche.cv else None,
        "completion": fiche.completion(),
        "resume": [{"titre": t, "valeurs": v} for t, v in _resume(user)],
    }


@extend_schema(tags=["profil"], responses=s.ProfilSerializer)
@api_view(["GET"])
def profil(request):
    """GET /api/v1/profil/ — toutes les sections du profil."""
    return Response(s.ProfilSerializer(profil_dict(request.user)).data)


def _vue_section(nom, serialiseur):
    """PUT /api/v1/profil/<nom>/ : une vue par section, pour un schema exact de chacune."""
    def vue(request):
        user = request.user
        saisie = serialiseur(data=request.data, context={
            "instance": Preferences.de(user) if nom == "preferences" else Profil.de(user),
            "fichiers": request.FILES})
        saisie.is_valid(raise_exception=True)
        saisie.save()
        return Response(s.ProfilSerializer(profil_dict(user)).data)
    vue.__name__ = f"profil_{nom}"
    vue.__doc__ = (f"PUT /api/v1/profil/{nom}/ — remplace la section « {nom} » "
                   "(la section complète, au format de GET /profil/).")
    vue = parser_classes([JSONParser, MultiPartParser, FormParser])(vue)
    vue = api_view(["PUT"])(vue)
    return extend_schema(tags=["profil"], operation_id=f"profil_{nom}_remplacer",
                         request={"application/json": serialiseur, "multipart/form-data": serialiseur},
                         responses={200: s.ProfilSerializer, **ERREURS})(vue)


profil_perso = _vue_section("perso", s.PersoSerializer)
profil_pro = _vue_section("pro", s.ProSerializer)
profil_domaines = _vue_section("domaines", s.DomainesSerializer)
profil_preferences = _vue_section("preferences", s.PreferencesSerializer)


@extend_schema(tags=["profil"], methods=["GET"], responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
@extend_schema(tags=["profil"], methods=["POST"], request={"multipart/form-data": s.CvDepotSerializer},
               responses={201: s.CvSerializer, **ERREURS})
@extend_schema(tags=["profil"], methods=["DELETE"], responses={204: None})
@api_view(["GET", "POST", "DELETE"])
@parser_classes([MultiPartParser, FormParser])
@renderer_classes([JSONRenderer, Binaire])
@throttle_classes([UserRateThrottle, TeleversementThrottle])
def profil_cv(request):
    """GET|POST|DELETE /api/v1/profil/cv/ — télécharger, déposer (multipart « fichier »), supprimer le CV."""
    from .views_profil import cv
    fiche = Profil.de(request.user)
    if request.method == "GET":
        return cv(request._request, request.user.pk)
    if request.method == "DELETE":
        supprimer_cv(fiche)
        return Response(status=status.HTTP_204_NO_CONTENT)
    saisie = s.CvDepotSerializer(data=request.data, context={"fichiers": request.FILES})
    saisie.is_valid(raise_exception=True)
    deposer_cv(fiche, saisie.form.cleaned_data["fichier"])
    return Response(s.CvSerializer({"nom": fiche.cv_nom, "depose_le": fiche.cv_depose_le}).data,
                    status=status.HTTP_201_CREATED)


@extend_schema(tags=["profil"], responses={(200, "image/*"): OpenApiTypes.BINARY})
@api_view(["GET"])
@renderer_classes([JSONRenderer, Binaire])
def profil_photo(request):
    """GET /api/v1/profil/photo/ — la photo de profil (image)."""
    from .views_profil import photo
    return photo(request._request, request.user.pk)


@extend_schema(tags=["compte"], parameters=PAGINATION, responses=PageNotifications)
@api_view(["GET"])
def notifications(request):
    """GET /api/v1/notifications/ — les offres envoyées par email, les plus récentes d'abord."""
    lot = Notification.objects.filter(user=request.user).select_related("offre")
    return paginer(request, lot, s.NotificationSerializer, taille=30,
                   alertes_actives=Preferences.de(request.user).notifications)


@extend_schema(tags=["abonnements"], methods=["GET"], responses=s.MesAbonnementsSerializer)
@extend_schema(tags=["abonnements"], methods=["POST"], request=s.DemandeSerializer,
               responses={201: s.DemandeCreeeSerializer, 409: s.ErreurSerializer, **ERREURS})
@api_view(["GET", "POST"])
def abonnements(request):
    """GET|POST /api/v1/abonnements/ — mes demandes et crédits ; demander un plan."""
    user = request.user
    if request.method == "POST":
        plan = _saisie(s.DemandeSerializer, request)["plan"]
        demande = appliquer(demander_plan, user, plan, statut=status.HTTP_409_CONFLICT)
        return Response({"message": f"Demande « {plan.nom} » envoyée. Elle sera activée à réception du paiement.",
                         "abonnement": s.AbonnementSerializer(demande).data}, status=status.HTTP_201_CREATED)
    return Response(s.MesAbonnementsSerializer({
        "credits": s.credits(user), "abonnements": user.abonnements.select_related("plan")[:50]}).data)


# ------------------------------------------------------------ admin offres

@extend_schema(tags=["admin"], request=s.DecisionSerializer,
               responses={200: s.SuiviSerializer, 201: s.SuiviSerializer, **ERREURS})
@api_view(["POST"])
@permission_classes(ADMIN)
def admin_decision(request, offre_id):
    """POST /api/v1/admin/offres/<id>/decision/ — pose ou change le statut commercial."""
    fiche = get_object_or_404(Offre, pk=offre_id)
    suivi, cree = appliquer(operations.decider_offre, fiche, _saisie(s.DecisionSerializer, request),
                            request.user)
    return Response(s.SuiviSerializer(suivi).data, status=201 if cree else 200)


@extend_schema(tags=["admin"], request=s.EcheanceSerializer, responses={200: s.SuiviSerializer, **ERREURS})
@api_view(["POST"])
@permission_classes(ADMIN)
def admin_echeance(request, offre_id):
    """POST /api/v1/admin/offres/<id>/echeance/ — saisit l'échéance qu'une source ne publie pas."""
    fiche = get_object_or_404(Offre, pk=offre_id)
    _, suivi = appliquer(operations.dater_offre, fiche, _saisie(s.EcheanceSerializer, request)["echeance"],
                         request.user)
    return Response(s.SuiviSerializer(suivi).data)


@extend_schema(tags=["admin"], request=s.VerdictSerializer, responses={200: s.VerdictSerializer, **ERREURS})
@api_view(["POST"])
@permission_classes(ADMIN)
def admin_verdict(request, offre_id):
    """POST /api/v1/admin/offres/<id>/verdict/ — corrige le verdict du tri (retenue ou écartée)."""
    fiche = get_object_or_404(Offre, pk=offre_id)
    pertinent = _saisie(s.VerdictSerializer, request)["pertinent"]
    return Response({"pertinent": appliquer(operations.juger_offre, fiche, pertinent)})


@extend_schema(tags=["admin"], responses=s.StatistiquesSerializer)
@api_view(["GET"])
@permission_classes(ADMIN)
def admin_statistiques(request):
    """GET /api/v1/admin/statistiques/ — compteurs pour un tableau de bord."""
    return Response(s.StatistiquesSerializer(donnees_statistiques()).data)


@extend_schema(tags=["admin"], responses=s.SourceSerializer(many=True))
@api_view(["GET"])
@permission_classes(ADMIN)
def admin_sources(request):
    """GET /api/v1/admin/sources/ — chaque source, ses volumes et sa dernière collecte."""
    return Response(s.SourceSerializer(donnees_sources(), many=True).data)


@extend_schema(tags=["admin"], responses=PageSuivi, parameters=[
    OpenApiParameter("statut", str, enum=[c for c, _ in Suivi.STATUT_CHOICES])] + PAGINATION)
@api_view(["GET"])
@permission_classes(ADMIN)
def admin_suivi(request):
    """GET /api/v1/admin/suivi/ — les décisions commerciales, les plus récentes d'abord."""
    lot = Suivi.objects.select_related("offre", "decide_par", "decide_par_cle").order_by("-maj_le")
    statut = request.GET.get("statut", "")
    if statut in dict(Suivi.STATUT_CHOICES):
        lot = lot.filter(statut=statut)
    return paginer(request, lot, s.SuiviLigneSerializer, taille=40)


@extend_schema(tags=["admin"], parameters=PARAMETRES_LISTE + [OpenApiParameter("format", str, enum=["csv", "json"])],
               responses={(200, "text/csv"): OpenApiTypes.BINARY, (200, "application/json"): OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes(ADMIN)
@renderer_classes([JSONRenderer, Binaire])
def admin_exporter(request):
    """GET /api/v1/admin/exporter/ — la sélection (mêmes filtres que la liste) en CSV ou JSON."""
    from .views_web import exporter
    return exporter(request._request)


# ------------------------------------------------------- admin abonnements

@extend_schema(tags=["admin"], responses=PageAbonnements, parameters=[
    OpenApiParameter("statut", str, enum=[c for c, _ in Abonnement.STATUTS])] + PAGINATION)
@api_view(["GET"])
@permission_classes(ADMIN)
def admin_abonnements(request):
    """GET /api/v1/admin/abonnements/ — toutes les demandes d'abonnement."""
    lot = Abonnement.objects.select_related("user", "plan", "valide_par")
    statut = request.GET.get("statut", "")
    if statut in dict(Abonnement.STATUTS):
        lot = lot.filter(statut=statut)
    return paginer(request, lot, s.AbonnementAdminSerializer, taille=30,
                   en_attente=Abonnement.objects.filter(statut=Abonnement.EN_ATTENTE).count())


def _demande_en_attente(abonnement_id):
    return get_object_or_404(Abonnement.objects.select_related("user", "plan"),
                             pk=abonnement_id, statut=Abonnement.EN_ATTENTE)


@extend_schema(tags=["admin"], request=None, responses={200: s.AbonnementAdminSerializer, **ERREURS})
@api_view(["POST"])
@permission_classes(ADMIN)
def admin_abonnement_valider(request, abonnement_id):
    """POST /api/v1/admin/abonnements/<id>/valider/ — paiement reçu : les crédits sont actifs."""
    demande = _demande_en_attente(abonnement_id)
    demande.valider(request.user)
    return Response(s.AbonnementAdminSerializer(demande).data)


@extend_schema(tags=["admin"], request=None, responses={200: s.AbonnementAdminSerializer, **ERREURS})
@api_view(["POST"])
@permission_classes(ADMIN)
def admin_abonnement_refuser(request, abonnement_id):
    """POST /api/v1/admin/abonnements/<id>/refuser/ — refuse une demande en attente."""
    demande = _demande_en_attente(abonnement_id)
    demande.refuser()
    return Response(s.AbonnementAdminSerializer(demande).data)


@extend_schema(tags=["admin"], methods=["GET"], responses=s.PlanSerializer(many=True))
@extend_schema(tags=["admin"], methods=["POST"], request=s.PlanSerializer,
               responses={201: s.PlanSerializer, **ERREURS})
@api_view(["GET", "POST"])
@permission_classes(ADMIN)
def admin_plans(request):
    """GET|POST /api/v1/admin/plans/ — tous les plans ; en créer un."""
    if request.method == "GET":
        return Response(s.PlanSerializer(Plan.objects.all(), many=True).data)
    saisie = s.PlanSerializer(data=request.data)
    saisie.is_valid(raise_exception=True)
    return Response(s.PlanSerializer(saisie.save()).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["admin"], methods=["GET"], responses=s.PlanSerializer)
@extend_schema(tags=["admin"], methods=["PUT", "PATCH"], request=s.PlanSerializer,
               responses={200: s.PlanSerializer, **ERREURS})
@api_view(["GET", "PUT", "PATCH"])
@permission_classes(ADMIN)
def admin_plan(request, plan_id):
    """GET|PUT|PATCH /api/v1/admin/plans/<id>/ — un plan ; le modifier (les abonnements validés gardent leurs crédits)."""
    plan = get_object_or_404(Plan, pk=plan_id)
    if request.method == "GET":
        return Response(s.PlanSerializer(plan).data)
    saisie = s.PlanSerializer(plan, data=request.data, partial=request.method == "PATCH")
    saisie.is_valid(raise_exception=True)
    return Response(s.PlanSerializer(saisie.save()).data)


# ------------------------------------------------------------ admin taches

@extend_schema(tags=["admin"], operation_id="admin_taches_etat", responses=s.TachesSerializer)
@api_view(["GET"])
@permission_classes(ADMIN)
def admin_taches(request):
    """GET /api/v1/admin/taches/ — tâche en cours, tâches à reprendre, historique, types lançables."""
    active = Tache.active()  # clot au passage une tache dont le processus est mort
    reglages = Parametres.charger()
    return Response(s.TachesSerializer({
        "active": active, "a_reprendre": Tache.objects.filter(statut__in=Tache.EN_ATTENTE),
        "automatismes_suspendus": reglages.automatismes_suspendus,
        "intervalle_collecte": reglages.intervalle_collecte,
        "types": [{"nom": nom, "libelle": libelle, "phases": phases}
                  for nom, (_, libelle, phases) in Tache.TYPES.items()],
        "nb_sources": len(REGISTRE_SCRAPERS), "historique": Tache.objects.all()[:20],
    }).data)


@extend_schema(tags=["admin"], operation_id="admin_tache_detail", responses={200: s.TacheDetailSerializer, **ERREURS})
@api_view(["GET"])
@permission_classes(ADMIN)
def admin_tache(request, tache_id):
    """GET /api/v1/admin/taches/<id>/ — une tâche et son journal (à interroger pendant qu'elle tourne)."""
    return Response(s.TacheDetailSerializer(get_object_or_404(Tache, pk=tache_id)).data)


def _tache_lancee(fonction, *args):
    tache, message, niveau = appliquer(fonction, *args)
    # 409 : une autre tache tournait deja, c'est elle qui est renvoyee.
    return Response({"message": message, "tache": s.TacheSerializer(tache).data},
                    status=status.HTTP_409_CONFLICT if niveau == "info" else status.HTTP_200_OK)


REPONSES_TACHE = {200: s.TacheReponseSerializer, 409: s.TacheReponseSerializer, **ERREURS}
ACTIONS_TACHE = ["suspendre", "annuler", "reprendre"]


@extend_schema(tags=["admin"], request=None, responses=REPONSES_TACHE,
               parameters=[_chemin("nom", Tache.TYPES)])
@api_view(["POST"])
@permission_classes(ADMIN)
def admin_tache_lancer(request, nom):
    """POST /api/v1/admin/taches/lancer/<nom>/ — lance une tâche de fond (une à la fois)."""
    return _tache_lancee(operations.lancer_tache, nom)


@extend_schema(tags=["admin"], operation_id="admin_tache_action", request=None, responses=REPONSES_TACHE,
               parameters=[_chemin("action", ACTIONS_TACHE)])
@api_view(["POST"])
@permission_classes(ADMIN)
def admin_tache_action(request, tache_id, action):
    """POST /api/v1/admin/taches/<id>/<action>/ — suspendre, annuler ou reprendre une tâche."""
    tache = get_object_or_404(Tache, pk=tache_id)
    if action == "reprendre" and tache.statut in Tache.EN_ATTENTE:
        return _tache_lancee(operations.reprendre_tache, tache)
    message = appliquer(operations.arreter_tache, tache, action)
    tache.refresh_from_db()
    return Response({"message": message, "tache": s.TacheSerializer(tache).data})


@extend_schema(tags=["admin"], request=None, parameters=[_chemin("action", ACTIONS_TACHE)],
               responses={200: s.MessageSerializer, 409: s.TacheReponseSerializer, **ERREURS})
@api_view(["POST"])
@permission_classes(ADMIN)
def admin_taches_toutes(request, action):
    """POST /api/v1/admin/taches/toutes/<action>/ — toutes les tâches et les automatismes."""
    message, a_reprendre = appliquer(operations.agir_sur_toutes, action)
    if a_reprendre:
        return _tache_lancee(operations.reprendre_tache, a_reprendre)
    return Response({"message": message})


# -------------------------------------------------------- admin parametres

@extend_schema(tags=["admin"], responses=s.ParametresSerializer)
@api_view(["GET"])
@permission_classes(ADMIN)
def admin_parametres(request):
    """GET /api/v1/admin/parametres/ — collecte, email (sans mot de passe), pondération, sources."""
    reglages = Parametres.charger()
    contexte = _contexte_parametres(reglages)
    return Response(s.ParametresSerializer({
        "collecte": {"intervalle_collecte": reglages.intervalle_collecte,
                     "heure_nuit": f"{reglages.heure_nuit:%H:%M}", "prochaine": contexte["prochain"],
                     "automatismes_suspendus": reglages.automatismes_suspendus,
                     "derniere_auto": contexte["dernier_auto"], "derniere_nuit": contexte["derniere_nuit"]},
        "email": {"source": operations.source_email(reglages), "smtp_hote": reglages.smtp_hote,
                  "smtp_port": reglages.smtp_port, "smtp_securite": reglages.smtp_securite,
                  "smtp_utilisateur": reglages.smtp_utilisateur,
                  "mot_de_passe_enregistre": bool(reglages.smtp_mot_de_passe),
                  "destinataires": reglages.liste_destinataires(),
                  "securites": s.choix(Parametres.SECURITES_SMTP)},
        "pertinence": [{"code": c, "libelle": l, "poids": p}
                       for c, l, p in _contexte_pertinence(reglages)["criteres_score"]],
        "sources": [{"source": l["scraper"].source_key, "nom": l["scraper"].nom, "site": l["scraper"].site,
                     "domaine": l["domaine"], "total": l["total"], "derniere": l["derniere"]}
                    for l in _contexte_sources()["lignes_sources"]],
    }).data)


@extend_schema(tags=["admin"], request=s.CollecteSerializer, responses={200: s.MessageSerializer, **ERREURS})
@api_view(["POST"])
@permission_classes(ADMIN)
def admin_parametres_collecte(request):
    """POST /api/v1/admin/parametres/collecte/ — fréquence de la collecte et heure de la nuit."""
    donnees = _saisie(s.CollecteSerializer, request)
    return Response({"message": appliquer(operations.regler_collecte, Parametres.charger(),
                                          donnees["intervalle_collecte"], donnees.get("heure_nuit", ""))})


@extend_schema(tags=["admin"], request=s.EmailSerializer, responses={200: s.EmailEnregistreSerializer, **ERREURS})
@api_view(["POST"])
@permission_classes(ADMIN)
def admin_parametres_email(request):
    """POST /api/v1/admin/parametres/email/ — serveur SMTP et destinataires (mot de passe vide = inchangé)."""
    donnees = dict(_saisie(s.EmailSerializer, request))
    donnees["destinataires"] = ", ".join(donnees.get("destinataires", []))
    message, efface = appliquer(operations.regler_email, Parametres.charger(), donnees)
    return Response({"message": message, "mot_de_passe_efface": efface})


@extend_schema(tags=["admin"], request=None, responses={200: s.EmailTestSerializer, **ERREURS})
@api_view(["POST"])
@permission_classes(ADMIN)
def admin_parametres_email_tester(request):
    """POST /api/v1/admin/parametres/email/tester/ — envoie un email de test."""
    message, niveau = appliquer(operations.tester_email)
    return Response({"message": message, "niveau": niveau})


@extend_schema(tags=["admin"], request=s.PoidsSerializer, responses={200: s.MessageSerializer, **ERREURS})
@api_view(["POST"])
@permission_classes(ADMIN)
def admin_parametres_pertinence(request):
    """POST /api/v1/admin/parametres/pertinence/ — pondération du score de correspondance (0 à 100)."""
    return Response({"message": appliquer(operations.regler_poids, Parametres.charger(),
                                          _saisie(s.PoidsSerializer, request))})


# ------------------------------------------------------ admin catalogues

CATALOGUES = {
    "secteurs": (Secteur, "secteur", _contexte_secteurs, operations.creer_secteur,
                 operations.renommer_secteur, operations.basculer_secteur, operations.retirer_secteur),
    "pays": (Pays, "pays", _contexte_pays, operations.creer_pays,
             operations.renommer_pays, operations.basculer_pays, operations.retirer_pays),
}


@extend_schema(tags=["admin"], methods=["GET"], operation_id="admin_catalogue_liste",
               responses=s.CatalogueSerializer(many=True), parameters=[_chemin("catalogue", CATALOGUES)])
@extend_schema(tags=["admin"], methods=["POST"], operation_id="admin_catalogue_ajouter", request=s.NomSerializer,
               responses={201: s.MessageSerializer, **ERREURS}, parameters=[_chemin("catalogue", CATALOGUES)])
@api_view(["GET", "POST"])
@permission_classes(ADMIN)
def admin_catalogue(request, catalogue):
    """GET|POST /api/v1/admin/<secteurs|pays>/ — le catalogue avec le nombre d'offres ; ajouter {"nom"}."""
    _, champ, contexte, creer, *_ = CATALOGUES[catalogue]
    if request.method == "GET":
        return Response(s.CatalogueSerializer([{
            "id": l[champ].pk, "code": l[champ].code, "nom": l[champ].nom, "actif": l[champ].actif,
            "nombre_offres": l["nombre_offres"]} for l in contexte()[f"lignes_{catalogue}"]], many=True).data)
    message = appliquer(creer, _saisie(s.NomSerializer, request)["nom"])
    return Response({"message": message}, status=status.HTTP_201_CREATED)


@extend_schema(tags=["admin"], methods=["PATCH"], operation_id="admin_catalogue_renommer", request=s.NomSerializer,
               responses={200: s.MessageSerializer, **ERREURS}, parameters=[_chemin("catalogue", CATALOGUES)])
@extend_schema(tags=["admin"], methods=["DELETE"], operation_id="admin_catalogue_retirer",
               responses={200: s.MessageSerializer, **ERREURS}, parameters=[_chemin("catalogue", CATALOGUES)])
@api_view(["PATCH", "DELETE"])
@permission_classes(ADMIN)
def admin_catalogue_element(request, catalogue, objet_id):
    """PATCH|DELETE /api/v1/admin/<secteurs|pays>/<id>/ — renommer {"nom"} ; retirer des choix (les offres restent)."""
    modele, _, _, _, renommer, _, retirer = CATALOGUES[catalogue]
    objet = get_object_or_404(modele, pk=objet_id)
    if request.method == "DELETE":
        return Response({"message": appliquer(retirer, objet)})
    return Response({"message": appliquer(renommer, objet, _saisie(s.NomSerializer, request)["nom"])})


@extend_schema(tags=["admin"], operation_id="admin_catalogue_basculer", request=None,
               responses={200: s.MessageSerializer, **ERREURS}, parameters=[_chemin("catalogue", CATALOGUES)])
@api_view(["POST"])
@permission_classes(ADMIN)
def admin_catalogue_basculer(request, catalogue, objet_id):
    """POST /api/v1/admin/<secteurs|pays>/<id>/basculer/ — activer ou désactiver dans les filtres."""
    modele, *_, basculer, _ = CATALOGUES[catalogue]
    return Response({"message": appliquer(basculer, get_object_or_404(modele, pk=objet_id))})


# ---------------------------------------------------------- admin cles

@extend_schema(tags=["admin"], methods=["GET"], responses=s.CleSerializer(many=True))
@extend_schema(tags=["admin"], methods=["POST"], request=s.NomSerializer,
               responses={201: s.CleCreeeSerializer, **ERREURS})
@api_view(["GET", "POST"])
@permission_classes(ADMIN)
def admin_cles(request):
    """GET|POST /api/v1/admin/cles/ — clés d'API machine ; en créer une (le jeton n'est montré qu'une fois)."""
    if request.method == "GET":
        return Response(s.CleSerializer(CleApi.objects.all(), many=True).data)
    nom = _saisie(s.NomSerializer, request)["nom"]
    jeton = appliquer(operations.creer_cle, nom)
    return Response({"message": f"Clé « {nom.strip()[:80]} » créée.", "jeton": jeton},
                    status=status.HTTP_201_CREATED)


@extend_schema(tags=["admin"], responses={200: s.MessageSerializer, **ERREURS})
@api_view(["DELETE"])
@permission_classes(ADMIN)
def admin_cle(request, cle_id):
    """DELETE /api/v1/admin/cles/<id>/ — révoque une clé machine."""
    CleApi.objects.filter(pk=cle_id, revoque_le__isnull=True).update(revoque_le=timezone.now())
    return Response({"message": "Clé révoquée."})
