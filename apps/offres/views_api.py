"""API REST sur les offres : lecture, et ecriture des decisions humaines.

Django seul, sans DRF : une dizaine de points d'entree, dont trois en
ecriture, ne justifient pas une dependance de plus. La serialisation tient en
quelques lignes, et la protection par jeton est celle de auth.py.

Lecture
    GET /api/offres/               liste filtree, paginee
    GET /api/offres/<id>/          fiche, description et suivi compris
    GET /api/statistiques/         compteurs pour un tableau de bord
    GET /api/sources/              les sources et leurs volumes
    GET /api/secteurs/             les cinq secteurs suivis
    GET /api/regions/              les regions, avec les lieux qui en relevent
    GET /api/carte/points/         les offres agregees par lieu
    GET /api/suivi/                les decisions commerciales

Ecriture -- ce que l'interface web permet, ouvert aux outils externes.
Corps JSON, reponse JSON, POST uniquement : un GET qui modifie l'etat serait
declenche par un prechargement ou un robot d'indexation.
    POST /api/offres/<id>/decision/   {"statut": "candidature", "note": "..."}
    POST /api/offres/<id>/echeance/   {"echeance": "2026-10-01"}
    POST /api/offres/<id>/verdict/    {"pertinent": true}

Chaque decision prise par l'API garde la CLE qui l'a prise (suivi.
decide_par_cle), comme une decision prise a l'ecran garde son auteur.

Les vues d'ecriture sont exemptees du jeton CSRF : ce mecanisme protege un
navigateur porteur d'une session, or ici l'appelant est un programme qui
presente un jeton d'API a chaque requete -- c'est lui, la preuve d'intention.
"""

import json
from datetime import date

from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .services import geo
from .auth import token_requis
from .models import Offre, Suivi
from .models import actionnables as _actionnables, ouvertes as _ouvertes
from .views_web import SECTEURS, agreger_par_lieu

#: Plafond dur. Sans lui, ?limite=100000 serialiserait toute la base en une
#: reponse -- une denial-of-service involontaire au premier script maladroit.
LIMITE_MAX = 200
LIMITE_DEFAUT = 50

#: Longueur maximale d'une note. Une note est un motif ou une consigne, pas
#: un dossier ; au-dela, c'est presque surement un corps mal adresse.
NOTE_MAX = 2000


def json_(donnees, statut: int = 200) -> JsonResponse:
    return JsonResponse(donnees, status=statut,
                        json_dumps_params={"ensure_ascii": False})


def erreur(message: str, statut: int = 400) -> JsonResponse:
    return json_({"erreur": message}, statut)


def serialiser_suivi(suivi) -> dict | None:
    if suivi is None:
        return None
    return {
        "statut": suivi.statut,
        "statut_libelle": suivi.get_statut_display(),
        "note": suivi.note,
        "echeance": suivi.echeance.isoformat() if suivi.echeance else None,
        "decide_par": (suivi.decide_par.username if suivi.decide_par_id else None),
        "decide_par_cle": (suivi.decide_par_cle.nom if suivi.decide_par_cle_id else None),
        "maj_le": suivi.maj_le.isoformat(),
    }


def serialiser(offre: Offre, complet: bool = False) -> dict:
    suivi = _suivi_de(offre)
    donnees = {
        "id": offre.id,
        "source": offre.source,
        "titre": offre.titre,
        "organisation": offre.organisation,
        "pays": offre.pays,
        "region": geo.region(offre.pays),
        "date_limite": offre.date_limite.isoformat() if offre.date_limite else None,
        "date_publication": (offre.date_publication.isoformat()
                             if offre.date_publication else None),
        "jours_restants": offre.jours_restants,
        "pertinent": offre.pertinent,
        "nature": offre.nature,
        "secteur": offre.secteur,
        "categorie": offre.categorie,
        "lien": offre.lien,
        "lien_etat": offre.lien_etat,
        # Le statut seul suffit dans une liste ; la fiche donne le reste.
        "suivi": suivi.statut if suivi else None,
    }
    if complet:
        donnees["description"] = offre.description
        donnees["raison"] = offre.raison
        donnees["date_ajout"] = offre.date_ajout.isoformat()
        donnees["suivi"] = serialiser_suivi(suivi)
    return donnees


def _suivi_de(offre):
    """Le suivi d'une offre, ou None -- sans lever quand il n'existe pas."""
    try:
        return offre.suivi
    except Suivi.DoesNotExist:
        return None


def _entier(requete, nom: str, defaut: int, maximum: int) -> int:
    try:
        valeur = int(requete.GET.get(nom, defaut))
    except (TypeError, ValueError):
        return defaut
    return max(0, min(valeur, maximum))


def _corps_json(requete) -> dict:
    """Le corps de la requete decode, ou une ValueError qui dit pourquoi."""
    if not requete.body:
        raise ValueError("Corps vide : un objet JSON est attendu.")
    try:
        corps = json.loads(requete.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Corps illisible : un objet JSON est attendu.")
    if not isinstance(corps, dict):
        raise ValueError("Le corps doit etre un objet JSON, pas une liste.")
    return corps


def _offre_ou_404(offre_id: str) -> Offre:
    try:
        return Offre.objects.select_related("suivi").get(pk=offre_id)
    except Offre.DoesNotExist:
        raise Http404(f"Offre {offre_id} introuvable.")




def _repartition():
    """Les lieux presents en base, classes par region."""
    return geo.repartir(Offre.objects.values_list("pays", flat=True).distinct())


def _dans_les_lieux(lot, lieux):
    """Restreint aux offres dont le pays est l'un des lieux.

    Un pays absent (NULL) fait partie de la region "inconnue" mais n'est
    jamais egal a rien : `pays__in` le manquerait, il faut le nommer.
    """
    lieux = list(lieux or [])
    if None in lieux:
        return lot.filter(Q(pays__in=[l for l in lieux if l is not None])
                          | Q(pays__isnull=True))
    return lot.filter(pays__in=lieux)


# --------------------------------------------------------------- lecture

@require_GET
@token_requis
def liste(requete):
    """GET /api/offres/

    Sert par defaut les offres RETENUES et ENCORE OUVERTES : c'est ce sur quoi
    on peut agir. Deux interrupteurs elargissent la vue :
      ?ecartees=1   inclut les offres jugees non pertinentes
      ?cloturees=1  inclut celles dont la date limite est passee

    Filtres : ?nature=marche|emploi ?secteur= ?source= ?categorie= ?pays=
              ?region=madagascar|ocean-indien|afrique|... ?lieu= ?suivi=
              ?q=
    Pagination : ?limite= (max 200) ?depuis=
    """
    lot = Offre.objects.select_related("suivi")

    # Les ecartees sont conservees en base pour auditer un changement de
    # criteres, pas pour etre servies au quotidien.
    if requete.GET.get("ecartees") != "1":
        lot = lot.filter(pertinent=True)
    if requete.GET.get("cloturees") != "1":
        lot = _ouvertes(lot)

    for champ in ("nature", "secteur", "source", "categorie", "pays"):
        valeur = requete.GET.get(champ)
        if valeur:
            lot = lot.filter(**{f"{champ}__iexact": valeur})

    # La region n'existe pas en base : on la traduit en la liste des lieux
    # qui en relevent, et c'est PostgreSQL qui filtre.
    region = requete.GET.get("region") or ""
    if region in geo.LIBELLE:
        lot = _dans_les_lieux(lot, _repartition().get(region, []))

    lieu = requete.GET.get("lieu") or ""
    if lieu:
        lot = lot.filter(pays=lieu)

    suivi = requete.GET.get("suivi") or ""
    if suivi in dict(Suivi.STATUT_CHOICES):
        lot = lot.filter(suivi__statut=suivi)
    elif suivi == "aucun":
        lot = lot.filter(suivi__isnull=True)

    recherche = (requete.GET.get("q") or "").strip()
    if recherche:
        lot = lot.filter(Q(titre__icontains=recherche)
                         | Q(organisation__icontains=recherche)
                         | Q(categorie__icontains=recherche))

    total = lot.count()
    depuis = _entier(requete, "depuis", 0, 1_000_000)
    limite = _entier(requete, "limite", LIMITE_DEFAUT, LIMITE_MAX)
    page = lot[depuis:depuis + limite]

    return json_({
        "total": total,
        "depuis": depuis,
        "limite": limite,
        "offres": [serialiser(o) for o in page],
    })


@require_GET
@token_requis
def detail(requete, offre_id: str):
    """GET /api/offres/<id>/ — avec la description complete et le suivi."""
    return json_(serialiser(_offre_ou_404(offre_id), complet=True))


@require_GET
@token_requis
def statistiques(requete):
    """GET /api/statistiques/ — de quoi alimenter un tableau de bord."""
    aujourdhui = timezone.now().date()
    base = Offre.objects.filter(pertinent=True)

    return json_({
        "total": Offre.objects.count(),
        "retenues": base.count(),
        "ouvertes": base.filter(Q(date_limite__gte=aujourdhui)
                                | Q(date_limite__isnull=True)).count(),
        "actionnables": _actionnables(Offre.objects.all()).count(),
        "par_nature": {(r["nature"] or "(non qualifiee)"): r["n"] for r in
                       base.values("nature").annotate(n=Count("id")).order_by("-n")},
        "par_secteur": {(r["secteur"] or "(non qualifie)"): r["n"] for r in
                        base.values("secteur").annotate(n=Count("id")).order_by("-n")},
        "par_source": {r["source"]: r["n"] for r in
                       base.values("source").annotate(n=Count("id")).order_by("-n")},
        "par_categorie": {r["categorie"] or "(sans)": r["n"] for r in
                          base.values("categorie").annotate(n=Count("id"))
                          .order_by("-n")[:15]},
        "par_region": {code: _dans_les_lieux(base, lieux).count()
                       for code, lieux in _repartition().items() if lieux},
        # Le seul chiffre qui dise si la veille sert : ce que les offres
        # retenues sont devenues, tel qu'un humain l'a tranche. Vide tant
        # que personne n'a rien decide, et c'est une reponse en soi.
        "suivi": {(r["statut"]): r["n"] for r in
                  Suivi.objects.values("statut").annotate(n=Count("id"))
                  .order_by("-n")},
    })


@require_GET
@token_requis
def sources(requete):
    """GET /api/sources/ — chaque source, ses volumes et sa derniere collecte.

    "actionnables" est le chiffre utile : ce qu'une source apporte
    aujourd'hui, pas ce qu'elle a apporte depuis son branchement.
    """
    actionnables = {r["source"]: r["n"] for r in
                    _actionnables(Offre.objects.all()).values("source")
                    .annotate(n=Count("id"))}
    lignes = (Offre.objects.values("source")
              .annotate(total=Count("id"),
                        retenues=Count("id", filter=Q(pertinent=True)),
                        derniere_collecte=Max("date_ajout"))
              .order_by("source"))
    return json_({"sources": [{
        "source": r["source"],
        "total": r["total"],
        "retenues": r["retenues"],
        "actionnables": actionnables.get(r["source"], 0),
        "derniere_collecte": r["derniere_collecte"].isoformat(),
    } for r in lignes]})


@require_GET
@token_requis
def secteurs(requete):
    """GET /api/secteurs/ — les cinq secteurs suivis, avec leurs volumes."""
    retenues = {r["secteur"]: r["n"] for r in
                Offre.objects.filter(pertinent=True).values("secteur")
                .annotate(n=Count("id"))}
    actionnables = {r["secteur"]: r["n"] for r in
                    _actionnables(Offre.objects.all()).values("secteur")
                    .annotate(n=Count("id"))}
    return json_({"secteurs": [{
        "code": code, "libelle": libelle,
        "retenues": retenues.get(code, 0),
        "actionnables": actionnables.get(code, 0),
    } for code, libelle in SECTEURS]})


@require_GET
@token_requis
def liste_regions(requete):
    """GET /api/regions/ — les regions, leurs lieux et leurs volumes.

    La region est deduite du lieu a l'affichage, pas stockee : cette route
    dit a quel code correspond quel lieu, pour qu'un client filtre juste.
    """
    repartition = _repartition()
    actionnables = _actionnables(Offre.objects.all())
    return json_({"regions": [{
        "code": code,
        "libelle": geo.LIBELLE[code],
        # Un pays absent releve de la region "inconnue" ; il n'a pas de nom
        # a lister, mais ses offres se comptent.
        "lieux": sorted(l for l in repartition.get(code, []) if l),
        "actionnables": (_dans_les_lieux(actionnables, repartition[code]).count()
                         if repartition.get(code) else 0),
    } for code, _ in geo.LIBELLES]})


@require_GET
@token_requis
def carte_points(requete):
    """GET /api/carte/points/ — les offres actionnables agregees par lieu.

    Memes filtres que /api/offres/ pour nature, secteur, source et region ;
    meme agregation que la carte de l'interface.
    """
    lot = _actionnables(Offre.objects.all())
    for champ in ("nature", "secteur", "source"):
        valeur = requete.GET.get(champ)
        if valeur:
            lot = lot.filter(**{f"{champ}__iexact": valeur})
    region = requete.GET.get("region") or ""
    if region in geo.LIBELLE:
        lot = _dans_les_lieux(lot, _repartition().get(region, []))
    return json_(agreger_par_lieu(lot))


@require_GET
@token_requis
def liste_suivi(requete):
    """GET /api/suivi/ — les decisions commerciales, les plus recentes d'abord.

    ?statut=a_etudier|candidature|gagne|perdu|hors_sujet
    """
    lot = Suivi.objects.select_related("offre", "decide_par", "decide_par_cle")
    statut = requete.GET.get("statut") or ""
    if statut in dict(Suivi.STATUT_CHOICES):
        lot = lot.filter(statut=statut)
    total = lot.count()
    depuis = _entier(requete, "depuis", 0, 1_000_000)
    limite = _entier(requete, "limite", LIMITE_DEFAUT, LIMITE_MAX)
    return json_({
        "total": total, "depuis": depuis, "limite": limite,
        "statuts": dict(Suivi.STATUT_CHOICES),
        "suivis": [{"offre": serialiser(s.offre), **serialiser_suivi(s)}
                   for s in lot[depuis:depuis + limite]],
    })


# -------------------------------------------------------------- ecriture

@csrf_exempt
@require_POST
@token_requis
def decision(requete, offre_id: str):
    """POST /api/offres/<id>/decision/ — pose ou change le statut commercial.

    Corps : {"statut": "a_etudier|candidature|gagne|perdu|hors_sujet",
             "note": "facultative"}
    La note absente laisse la note en place ; une note vide l'efface.
    """
    offre = _offre_ou_404(offre_id)
    try:
        corps = _corps_json(requete)
    except ValueError as exc:
        return erreur(str(exc))

    statut = corps.get("statut")
    if statut not in dict(Suivi.STATUT_CHOICES):
        return erreur(f"Statut inconnu. Attendu : {', '.join(dict(Suivi.STATUT_CHOICES))}.")
    champs = {"statut": statut, "decide_par": None,
              "decide_par_cle": requete.cle_api}
    if "note" in corps:
        note = corps.get("note")
        if note is not None and not isinstance(note, str):
            return erreur("La note doit etre une chaine.")
        note = (note or "").strip()
        if len(note) > NOTE_MAX:
            return erreur(f"Note trop longue ({len(note)} caracteres, maximum {NOTE_MAX}).")
        champs["note"] = note

    suivi, cree = Suivi.objects.update_or_create(offre_id=offre.pk, defaults=champs)
    return json_({"offre": offre.pk, "cree": cree, "suivi": serialiser_suivi(suivi)},
                 201 if cree else 200)


@csrf_exempt
@require_POST
@token_requis
def echeance(requete, offre_id: str):
    """POST /api/offres/<id>/echeance/ — saisit l'echeance qu'une source ne
    publie pas.

    Corps : {"echeance": "AAAA-MM-JJ"}
    Ecrite a deux endroits, comme a l'ecran : suivi.echeance, trace de la
    decision qui survit a tout re-tri, et offres.date_limite, ce que lisent
    toutes les vues sans jointure.
    """
    offre = _offre_ou_404(offre_id)
    try:
        corps = _corps_json(requete)
        brut = corps.get("echeance")
        if not isinstance(brut, str):
            raise ValueError("Champ 'echeance' attendu, au format AAAA-MM-JJ.")
        valeur = date.fromisoformat(brut.strip())
    except ValueError as exc:
        return erreur(str(exc) if "echeance" in str(exc)
                      else "Date illisible : attendu AAAA-MM-JJ.")

    maintenant = timezone.now()
    with transaction.atomic():
        suivi, _ = Suivi.objects.update_or_create(
            offre_id=offre.pk,
            defaults={"echeance": valeur, "echeance_saisie_le": maintenant,
                      "decide_par": None, "decide_par_cle": requete.cle_api})
        Offre.objects.filter(pk=offre.pk).update(date_limite=valeur, date_maj=maintenant)
    return json_({"offre": offre.pk, "date_limite": valeur.isoformat(),
                  "suivi": serialiser_suivi(suivi)})


@csrf_exempt
@require_POST
@token_requis
def verdict(requete, offre_id: str):
    """POST /api/offres/<id>/verdict/ — corrige le verdict du tri.

    Corps : {"pertinent": true|false}
    Meme portee que la case "retenue" de l'admin : c'est un verdict, qu'un
    humain peut vouloir corriger. Et meme limite : un re-tri (retrier.py)
    reecrit la ligne et peut le rendre. Pour ecarter durablement une offre,
    poser le statut "hors_sujet" par /decision/, qui survit au re-tri.
    """
    offre = _offre_ou_404(offre_id)
    try:
        corps = _corps_json(requete)
    except ValueError as exc:
        return erreur(str(exc))
    pertinent = corps.get("pertinent")
    if not isinstance(pertinent, bool):
        return erreur("Champ 'pertinent' attendu : true ou false.")
    Offre.objects.filter(pk=offre.pk).update(pertinent=pertinent, date_maj=timezone.now())
    return json_({"offre": offre.pk, "pertinent": pertinent})
