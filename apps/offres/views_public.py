"""API publique, en lecture, SANS authentification : /api/public/.

Elle alimente un site (Next.js) qui montre les offres a tout venant. Trois
regles la separent de l'API privee de views.py :

  - aucun jeton, et des en-tetes CORS pour qu'un navigateur l'appelle depuis
    une autre origine (API_PUBLIQUE_ORIGINES) ;
  - jamais le suivi commercial (qui a candidate, gagne, perdu -- c'est
    l'affaire de Label Technology), jamais les offres ecartees, et pas les
    sources listees dans API_PUBLIQUE_SOURCES_EXCLUES -- voir le rappel
    juridique dans settings.py ;
  - tout le reste de l'offre, localisation comprise : la position du lieu
    (geo.point) et sa region sont ajoutees a chaque offre, pour
    qu'une carte se dessine sans second appel.

Routes
    GET /api/public/                  index : les routes et leurs parametres
    GET /api/public/offres/           liste filtree, paginee, triable
    GET /api/public/offres/<id>/      une offre, description complete
    GET /api/public/statistiques/     compteurs
    GET /api/public/sources/          sources et volumes
    GET /api/public/secteurs/         les cinq secteurs suivis
    GET /api/public/regions/          regions, lieux, volumes
    GET /api/public/lieux/            chaque lieu avec ses coordonnees
    GET /api/public/carte/points/     offres agregees par lieu

Reponses en JSON UTF-8, jamais d'ASCII echappe. Les reponses sont
cacheables cinq minutes : les offres changent une fois par jour.
"""

from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.db.models import Count, Max, Q
from django.http import Http404, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .services import geo
from .models import Offre
from .views_api import (LIMITE_DEFAUT, LIMITE_MAX, _actionnables, _dans_les_lieux,
                    _entier, _ouvertes, _repartition, json_)
from .views_web import SECTEURS, URGENT, agreger_par_lieu

#: Colonnes acceptees par ?tri=. La valeur est le champ ORM, le signe le sens.
TRIS = {
    "echeance": ("date_limite", "id"),        # la plus proche d'abord
    "publication": ("-date_publication", "-date_ajout"),
    "ajout": ("-date_ajout",),
}

CACHE_SECONDES = 300


def _publique(vue):
    """Reponse JSON avec CORS et cache, et OPTIONS pour la preverification
    du navigateur. Pas de jeton : c'est le sens de ce namespace."""

    # csrf_exempt : sans lui, un POST egare recevrait un 403 "CSRF" avant
    # que require_http_methods ne dise 405. Rien n'ecrit ici, le jeton CSRF
    # n'a rien a proteger ; le refus doit dire la vraie raison.
    @wraps(vue)
    @csrf_exempt
    @require_http_methods(["GET", "OPTIONS"])
    def enveloppe(requete, *args, **kwargs):
        if requete.method == "OPTIONS":
            reponse = HttpResponse(status=204)
        else:
            reponse = vue(requete, *args, **kwargs)
            reponse["Cache-Control"] = f"public, max-age={CACHE_SECONDES}"
        reponse["Access-Control-Allow-Origin"] = settings.API_PUBLIQUE_ORIGINES
        reponse["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        reponse["Access-Control-Allow-Headers"] = "Content-Type"
        reponse["Access-Control-Max-Age"] = "86400"
        reponse["Vary"] = "Origin"
        return reponse

    return enveloppe


def _exposables():
    """Les offres que le public peut voir : retenues, hors sources exclues."""
    lot = Offre.objects.filter(pertinent=True)
    if settings.API_PUBLIQUE_SOURCES_EXCLUES:
        lot = lot.exclude(source__in=settings.API_PUBLIQUE_SOURCES_EXCLUES)
    return lot


def localisation(pays) -> dict:
    """Ce qu'il faut pour placer une offre : lieu, region, geo."""
    position = geo.point(pays)
    code = geo.region(pays)
    return {
        "lieu": (pays or "").strip() or None,
        "region": code,
        "region_libelle": geo.LIBELLE[code],
        "lat": position[0] if position else None,
        "lon": position[1] if position else None,
    }


def serialiser(offre: Offre, complet: bool = False) -> dict:
    restants = offre.jours_restants
    donnees = {
        "id": offre.id,
        "source": offre.source,
        "titre": offre.titre,
        "organisation": offre.organisation,
        "pays": offre.pays,
        "localisation": localisation(offre.pays),
        "nature": offre.nature,
        "secteur": offre.secteur,
        "categorie": offre.categorie,
        "date_publication": (offre.date_publication.isoformat()
                             if offre.date_publication else None),
        "date_limite": offre.date_limite.isoformat() if offre.date_limite else None,
        "jours_restants": restants,
        "urgente": restants is not None and 0 <= restants <= URGENT,
        "ouverte": offre.est_ouverte,
        "lien": offre.lien,
        "lien_etat": offre.lien_etat,
        "date_ajout": offre.date_ajout.isoformat(),
        "date_maj": offre.date_maj.isoformat(),
    }
    if complet:
        donnees["description"] = offre.description
        donnees["raison"] = offre.raison
    return donnees


def _filtrer(requete, lot):
    """Les filtres communs a la liste et a la carte."""
    for champ in ("nature", "secteur", "source", "categorie", "pays"):
        valeur = requete.GET.get(champ)
        if valeur:
            lot = lot.filter(**{f"{champ}__iexact": valeur})
    region = requete.GET.get("region") or ""
    if region in geo.LIBELLE:
        lot = _dans_les_lieux(lot, _repartition().get(region, []))
    lieu = requete.GET.get("lieu") or ""
    if lieu:
        lot = lot.filter(pays=lieu)
    urgence = requete.GET.get("urgence")
    if urgence and urgence.isdigit():
        borne = timezone.now().date() + timedelta(days=int(urgence))
        lot = lot.filter(date_limite__gte=timezone.now().date(), date_limite__lte=borne)
    recherche = (requete.GET.get("q") or "").strip()
    if recherche:
        lot = lot.filter(Q(titre__icontains=recherche)
                         | Q(organisation__icontains=recherche)
                         | Q(categorie__icontains=recherche)
                         | Q(description__icontains=recherche))
    return lot


@_publique
def index(requete):
    """GET /api/public/ — de quoi s'orienter sans lire le code."""
    base = requete.build_absolute_uri("/api/public/")
    return json_({
        "nom": "Veille appels d'offres — API publique",
        "authentification": "aucune",
        "cors": settings.API_PUBLIQUE_ORIGINES,
        "sources_exclues": settings.API_PUBLIQUE_SOURCES_EXCLUES,
        "routes": {
            "offres": {
                "url": base + "offres/",
                "filtres": ["nature=marche|emploi", "secteur=<code>", "source=<code>",
                            "categorie=", "pays=", "region=<code>", "lieu=",
                            "urgence=<jours>", "q=<mots>", "cloturees=1",
                            "tri=echeance|publication|ajout",
                            f"limite=<1..{LIMITE_MAX}>", "depuis=<n>"],
            },
            "offre": {"url": base + "offres/<id>/"},
            "statistiques": {"url": base + "statistiques/"},
            "sources": {"url": base + "sources/"},
            "secteurs": {"url": base + "secteurs/"},
            "regions": {"url": base + "regions/"},
            "lieux": {"url": base + "lieux/"},
            "carte": {"url": base + "carte/points/",
                      "filtres": ["nature", "secteur", "source", "region", "urgence", "q"]},
        },
    })


@_publique
def liste(requete):
    """GET /api/public/offres/

    Par defaut, les offres retenues ENCORE OUVERTES -- meme regle que
    l'interface. ?cloturees=1 ajoute celles dont l'echeance est passee.
    """
    lot = _exposables()
    if requete.GET.get("cloturees") != "1":
        lot = _ouvertes(lot)
    lot = _filtrer(requete, lot)

    tri = requete.GET.get("tri") or "ajout"
    lot = lot.order_by(*TRIS.get(tri, TRIS["ajout"]))

    total = lot.count()
    depuis = _entier(requete, "depuis", 0, 1_000_000)
    limite = _entier(requete, "limite", LIMITE_DEFAUT, LIMITE_MAX)
    page = lot[depuis:depuis + limite]
    return json_({
        "total": total, "depuis": depuis, "limite": limite,
        "tri": tri if tri in TRIS else "ajout",
        "offres": [serialiser(o) for o in page],
    })


@_publique
def detail(requete, offre_id: str):
    """GET /api/public/offres/<id>/ — description complete.

    Une offre ecartee ou d'une source exclue est introuvable, pas
    interdite : dire qu'elle existe serait deja en dire trop.
    """
    try:
        offre = _exposables().get(pk=offre_id)
    except Offre.DoesNotExist:
        raise Http404(f"Offre {offre_id} introuvable.")
    return json_(serialiser(offre, complet=True))


@_publique
def statistiques(requete):
    """GET /api/public/statistiques/"""
    base = _exposables()
    ouvertes = _ouvertes(base)
    aujourdhui = timezone.now().date()
    return json_({
        "retenues": base.count(),
        "ouvertes": ouvertes.count(),
        "urgentes": ouvertes.filter(
            date_limite__gte=aujourdhui,
            date_limite__lte=aujourdhui + timedelta(days=URGENT)).count(),
        "par_nature": {(r["nature"] or "non_qualifiee"): r["n"] for r in
                       ouvertes.values("nature").annotate(n=Count("id")).order_by("-n")},
        "par_secteur": {(r["secteur"] or "non_qualifie"): r["n"] for r in
                        ouvertes.values("secteur").annotate(n=Count("id")).order_by("-n")},
        "par_source": {r["source"]: r["n"] for r in
                       ouvertes.values("source").annotate(n=Count("id")).order_by("-n")},
        "par_region": {code: _dans_les_lieux(ouvertes, lieux).count()
                       for code, lieux in _repartition().items() if lieux},
        "derniere_collecte": (base.aggregate(d=Max("date_ajout"))["d"] or timezone.now()).isoformat(),
    })


@_publique
def sources(requete):
    """GET /api/public/sources/"""
    ouvertes = {r["source"]: r["n"] for r in
                _ouvertes(_exposables()).values("source").annotate(n=Count("id"))}
    lignes = (_exposables().values("source")
              .annotate(retenues=Count("id"), derniere_collecte=Max("date_ajout"))
              .order_by("source"))
    return json_({"sources": [{
        "source": r["source"],
        "retenues": r["retenues"],
        "ouvertes": ouvertes.get(r["source"], 0),
        "derniere_collecte": r["derniere_collecte"].isoformat(),
    } for r in lignes]})


@_publique
def secteurs(requete):
    """GET /api/public/secteurs/"""
    ouvertes = {r["secteur"]: r["n"] for r in
                _ouvertes(_exposables()).values("secteur").annotate(n=Count("id"))}
    return json_({"secteurs": [{"code": code, "libelle": libelle,
                                "ouvertes": ouvertes.get(code, 0)}
                               for code, libelle in SECTEURS]})


@_publique
def liste_regions(requete):
    """GET /api/public/regions/"""
    repartition = _repartition()
    ouvertes = _ouvertes(_exposables())
    return json_({"regions": [{
        "code": code,
        "libelle": geo.LIBELLE[code],
        "lieux": sorted(l for l in repartition.get(code, []) if l),
        "ouvertes": (_dans_les_lieux(ouvertes, repartition[code]).count()
                     if repartition.get(code) else 0),
    } for code, _ in geo.LIBELLES]})


@_publique
def lieux(requete):
    """GET /api/public/lieux/ — chaque lieu, ses coordonnees, ses offres ouvertes.

    Les lieux sans coordonnees sont servis aussi, avec lat et lon a null :
    un client peut les lister meme s'il ne peut pas les placer.
    """
    comptes = (_ouvertes(_exposables()).values("pays")
               .annotate(n=Count("id")).order_by("-n"))
    return json_({"lieux": [{**localisation(r["pays"]), "ouvertes": r["n"]}
                            for r in comptes if r["pays"]]})


@_publique
def carte_points(requete):
    """GET /api/public/carte/points/ — memes points que la carte de l'interface."""
    lot = _filtrer(requete, _actionnables(_exposables()))
    return json_(agreger_par_lieu(lot))
