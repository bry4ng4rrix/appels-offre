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
    GET /api/public/secteurs/         les secteurs connus et ceux deja presents
    GET /api/public/regions/          regions, lieux, volumes
    GET /api/public/lieux/            chaque lieu avec ses coordonnees
    GET /api/public/carte/points/     offres agregees par lieu

Reponses en JSON UTF-8, jamais d'ASCII echappe. Les reponses sont
cacheables cinq minutes : les offres changent une fois par jour.
"""

import json
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.db.models import Count, Max, Q
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .scrapers import REGISTRE_SCRAPERS
from .services import geo
from .models import Offre
from .views_api import (LIMITE_DEFAUT, LIMITE_MAX, _actionnables, _dans_les_lieux,
                    _entier, _ouvertes, _repartition, json_)
from .views_web import (URGENT, agreger_par_lieu, annoter, libelles_secteurs,
                        secteurs_disponibles)

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

    return login_not_required(enveloppe)


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
                               for code, libelle in secteurs_disponibles()]})


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


#: Page publique : combien d'offres a clotures proches, et dans quel delai.
VITRINE_NOMBRE = 20


#: Lieux dessines sur la carte d'en-tete : les plus fournis, assez pour couvrir le monde.
VITRINE_LIEUX = 80


def points_carte(lieux: list) -> list:
    """Position et rayon de chaque lieu dans le viewBox de _monde.svg, pour
    dessiner la carte cote serveur, sans JS. Meme projection que _carte_monde."""
    maximum = max((p["total"] for p in lieux), default=1)
    return [{"x": round((p["lon"] + 180) / 360 * 2000, 1), "y": round((84 - p["lat"]) / 140 * 800, 1),
             "r": round(6 + 22 * (p["total"] / maximum) ** .5, 1), "presse": p["urgentes"] > 0,
             "lieu": p["lieu"], "total": p["total"]} for p in lieux]


#: Nom affiche aux moteurs et aux reseaux, le meme que le logo de base.html.
MARQUE = "Label Collectes"


def json_ld(donnees) -> str:
    """JSON-LD a poser dans <script>. Les titres viennent des sources : un
    "</script>" dans l'un d'eux fermerait la balise, d'ou l'echappement."""
    texte = json.dumps(donnees, ensure_ascii=False)
    return mark_safe(texte.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def faq(total: int, sources: int) -> list:
    """Questions-reponses affichees ET balisees (FAQPage) : le balisage doit
    reprendre le texte visible, sinon Google l'ignore."""
    return [
        ("Qu'est-ce que Label Collectes ?",
         f"Une veille des appels d'offres et des offres d'emploi publiés par {sources} sources : "
         "bailleurs, agences des Nations unies, ONG et portails nationaux de marchés publics. "
         f"{total} offres collectées à ce jour, triées par secteur, pays et date limite."),
        ("Quelles offres sont affichées ici ?",
         "Celles qui clôturent dans les 7 prochains jours, de la plus proche à la plus lointaine. "
         "La carte montre toutes les offres ouvertes par lieu."),
        ("Comment accéder aux annonces officielles ?",
         "Créez un compte : vous ouvrez alors chaque annonce, la liste complète avec ses filtres, "
         "des suggestions selon votre profil et des alertes par email."),
    ]


@login_not_required
def vitrine(requete):
    """GET / — page HTML sans connexion : les 20 prochaines clotures sous
    URGENT jours. Le reste, annonces comprises, est reserve aux comptes.
    Connecte, l'accueil est la liste des offres : la vitrine ne lui apprendrait rien."""
    if requete.user.is_authenticated:
        return redirect("web-liste")
    aujourdhui = timezone.now().date()
    libelles = libelles_secteurs()
    urgentes = [annoter(o, aujourdhui, libelles) for o in
                (_actionnables(_exposables())
                 .filter(date_limite__gte=aujourdhui, date_limite__lte=aujourdhui + timedelta(days=URGENT))
                 .order_by("date_limite", "id")[:VITRINE_NOMBRE])]
    total = Offre.objects.count()
    questions = faq(total, len(REGISTRE_SCRAPERS))
    lieux = agreger_par_lieu(_actionnables(_exposables()))["points"][:VITRINE_LIEUX]
    accueil = requete.build_absolute_uri("/")
    return render(requete, "offres/vitrine.html", {
        "urgentes": urgentes,
        "total": total,
        "points": points_carte(lieux),
        "faq": questions,
        "json_ld": json_ld({"@context": "https://schema.org", "@graph": [
            {"@type": "WebSite", "@id": accueil + "#site", "url": accueil, "name": MARQUE,
             "inLanguage": "fr"},
            {"@type": "Organization", "@id": accueil + "#organisation", "name": MARQUE, "url": accueil},
            # Pas d'url par offre : les fiches exigent un compte, et un lien
            # vers une page fermee serait un lien mort pour le moteur.
            {"@type": "ItemList", "name": "Appels d'offres qui clôturent sous 7 jours",
             "numberOfItems": len(urgentes),
             "itemListElement": [{
                 "@type": "ListItem", "position": i, "name": o.titre_lisible,
                 "description": f"{o.organisation or 'Organisation non précisée'}"
                                f"{' · ' + o.pays if o.pays else ''} · clôture le {o.date_limite:%d/%m/%Y}",
             } for i, o in enumerate(urgentes, 1)]},
            {"@type": "FAQPage", "mainEntity": [{
                "@type": "Question", "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r in questions]},
        ]}),
    })


def _texte(contenu: str, type_mime: str = "text/plain; charset=utf-8") -> HttpResponse:
    reponse = HttpResponse(contenu, content_type=type_mime)
    reponse["Cache-Control"] = f"public, max-age={CACHE_SECONDES}"
    return reponse


@login_not_required
def robots(requete):
    """GET /robots.txt — seules l'accueil, la carte et l'API publique sont a explorer."""
    return _texte("\n".join([
        "User-agent: *",
        "Allow: /$",
        "Allow: /carte/$",
        "Allow: /api/public/",
        "Allow: /llms.txt",
        "Allow: /static/",
        "Disallow: /",
        "",
        f"Sitemap: {requete.build_absolute_uri('/sitemap.xml')}",
        "",
    ]))


@login_not_required
def sitemap(requete):
    """GET /sitemap.xml — les deux pages publiques, datees de la derniere collecte."""
    derniere = Offre.objects.aggregate(d=Max("date_ajout"))["d"] or timezone.now()
    urls = "".join(
        f"<url><loc>{requete.build_absolute_uri(chemin)}</loc>"
        f"<lastmod>{derniere.date().isoformat()}</lastmod><changefreq>daily</changefreq></url>"
        for chemin in ("/", "/carte/"))
    return _texte('<?xml version="1.0" encoding="UTF-8"?>'
                  f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
                  "application/xml; charset=utf-8")


@login_not_required
def llms(requete):
    """GET /llms.txt — presentation en Markdown pour les assistants IA (AEO) :
    ce qu'est le site, et ou lire les donnees sans analyser le HTML."""
    base = requete.build_absolute_uri("/")
    lignes = [f"# {MARQUE}", "",
              "> Veille d'appels d'offres et d'offres d'emploi internationaux, "
              "triés par secteur, pays et date limite.", ""]
    for question, reponse in faq(Offre.objects.count(), len(REGISTRE_SCRAPERS)):
        lignes += [f"## {question}", "", reponse, ""]
    lignes += ["## Pages et données publiques", "",
               f"- [Accueil]({base}) : les offres qui clôturent sous 7 jours",
               f"- [Carte]({base}carte/) : les offres ouvertes par lieu",
               f"- [API publique JSON]({base}api/public/) : offres, statistiques, secteurs, "
               "régions, sans authentification", ""]
    return _texte("\n".join(lignes))
