"""Interface web de consultation des offres. Sans connexion : application
mono-utilisateur, a ne servir que sur 127.0.0.1 (ou via tunnel SSH).

Deliberement separee de views.py, qui sert l'API. Les deux n'ont pas la meme
authentification -- session ici, jeton la-bas -- et les melanger dans un
fichier inviterait a poser le mauvais decorateur sur une nouvelle vue.

L'interface s'adresse a une personne devant un navigateur : elle passe donc
par la connexion Django, comme l'admin. Un jeton d'API n'aurait aucun sens
ici, il faudrait le coller dans un en-tete a chaque page.
"""

import csv
import json
from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .auth import empreinte, engendrer
from .models import PRESUMEE_CLOSE_JOURS, CleApi, Offre, Parametres, Suivi, Tache
from .services import geo
from .services.notification import NotificationService
from .services.taches import DejaEnCours, demarrer, prochaine_execution

#: Les domaines suivis, dans l'ordre d'affichage. Declares une seule fois :
#: le filtre, les compteurs et le gabarit s'y referent tous, et en ajouter un
#: sixieme ne demandera qu'une ligne ici.
SECTEURS = [("informatique", "Informatique"), ("construction", "Construction"),
            ("agriculture", "Agriculture"), ("eau", "Eau"),
            ("environnement", "Environnement")]
SECTEURS_SUIVIS = [code for code, _ in SECTEURS]

#: Offres par page. Au-dela, la page devient longue a parcourir sans gagner
#: en utilite : on vient ici pour reperer, pas pour tout lire.
PAR_PAGE = 25

#: Seuils d'urgence, en jours, pour colorer une echeance.
URGENT = 7
PROCHE = 21


def filtrer(requete):
    """Applique les filtres de l'URL a la liste des offres.

    Renvoie le queryset et un dictionnaire decrivant les filtres actifs, pour
    que le gabarit puisse les reafficher dans le formulaire.
    """
    aujourdhui = timezone.now().date()
    lot = Offre.objects.all()

    etat = requete.GET.get("etat") or "actionnables"
    limite_presomption = timezone.now() - timedelta(days=PRESUMEE_CLOSE_JOURS)
    # Une offre que sa source a retiree ou declaree close n'est plus
    # actionnable, quelle que soit son echeance affichee.
    ferme = Q(lien_etat__in=Offre.LIEN_FERME)

    if etat == "actionnables":
        # Le cas courant : ce sur quoi on peut encore agir. Une offre sans
        # echeance y figure tant qu'elle est recente ; passe PRESUMEE_CLOSE_JOURS
        # jours, elle en sort -- voir la constante pour le raisonnement.
        lot = lot.filter(pertinent=True).exclude(ferme).filter(
            Q(date_limite__gte=aujourdhui)
            | Q(date_limite__isnull=True,
                date_publication__gte=limite_presomption.date())
            | Q(date_limite__isnull=True, date_publication__isnull=True,
                date_ajout__gte=limite_presomption))
    elif etat == "retirees":
        # Constatees disparues ou closes chez la source.
        lot = lot.filter(pertinent=True).filter(ferme)
    elif etat == "sans-echeance":
        # Celles que la presomption ecarte : consultables a la demande, parce
        # qu'une presomption n'est pas une certitude.
        lot = lot.filter(pertinent=True, date_limite__isnull=True).filter(
            Q(date_publication__lt=limite_presomption.date())
            | Q(date_publication__isnull=True,
                date_ajout__lt=limite_presomption))
    elif etat == "retenues":
        lot = lot.filter(pertinent=True)
    elif etat == "ecartees":
        lot = lot.filter(pertinent=False)
    # "toutes" ne filtre rien.

    nature = requete.GET.get("nature") or ""
    if nature in ("marche", "emploi"):
        lot = lot.filter(nature=nature)
    elif nature == "inconnue":
        lot = lot.filter(nature__isnull=True)

    # Les cinq domaines suivis. "autre" n'est pas propose : par construction,
    # une offre "autre" n'est jamais pertinente, et l'exposer ferait croire a
    # une categorie consultable.
    secteur = requete.GET.get("secteur") or ""
    if secteur in SECTEURS_SUIVIS:
        lot = lot.filter(secteur=secteur)

    # La region n'existe pas en base : on traduit le filtre en la liste des
    # valeurs de `pays` qui en relevent, et c'est PostgreSQL qui filtre.
    # Classer 2969 lignes en Python couterait une lecture complete a chaque
    # page.
    demandee = requete.GET.get("region") or ""
    if demandee in geo.LIBELLE:
        lieux = geo.repartir(
            Offre.objects.values_list("pays", flat=True).distinct()
        ).get(demandee, [])
        lot = lot.filter(pays__in=lieux)

    # Lieu EXACT, tel qu'il figure en base. C'est ce que la carte passe quand
    # on clique un point : elle designe un lieu precis, pas une region.
    lieu = requete.GET.get("lieu") or ""
    if lieu:
        lot = lot.filter(pays=lieu)

    source = requete.GET.get("source") or ""
    if source:
        lot = lot.filter(source=source)

    recherche = (requete.GET.get("q") or "").strip()
    if recherche:
        lot = lot.filter(Q(titre__icontains=recherche)
                         | Q(organisation__icontains=recherche)
                         | Q(categorie__icontains=recherche))

    filtres = {"etat": etat, "nature": nature, "secteur": secteur,
               "source": source, "region": demandee, "lieu": lieu,
               "q": recherche}
    return lot, filtres


def urgence(offre, aujourdhui):
    """Qualifie l'echeance : sans date, presumee close, passee, urgente...

    Une offre SANS date limite n'est jamais dite close avec certitude : on ne
    peut pas l'affirmer. C'est le cas de toute la source BAD, dont l'echeance
    ne figure que dans le PDF du dossier. Passe PRESUMEE_CLOSE_JOURS jours depuis sa
    collecte, elle bascule en "presumee" -- l'ecran affiche alors son age, de
    sorte que le lecteur juge sur pieces plutot que sur un mot.
    """
    if not offre.date_limite:
        # La date de publication prime : elle dit l'age reel de l'avis, alors
        # que date_ajout ne dit que la date de notre collecte.
        if offre.date_publication:
            age = (aujourdhui - offre.date_publication).days
        else:
            age = (timezone.now() - offre.date_ajout).days
        if age >= PRESUMEE_CLOSE_JOURS:
            return "presumee", age
        return "inconnue", age
    jours = (offre.date_limite - aujourdhui).days
    if jours < 0:
        return "passee", jours
    if jours <= URGENT:
        return "urgente", jours
    if jours <= PROCHE:
        return "proche", jours
    return "lointaine", jours


def annoter(offre, aujourdhui=None):
    """Attributs d'affichage : etat d'echeance, region."""
    offre.etat_echeance, offre.jours = urgence(offre, aujourdhui or timezone.now().date())
    offre.region = geo.region(offre.pays)
    offre.region_libelle = geo.LIBELLE[offre.region]
    return offre


def _auteur(requete):
    """Interface sans connexion : l'auteur n'est connu que si une session admin existe."""
    return requete.user if requete.user.is_authenticated else None


def est_htmx(requete) -> bool:
    return requete.headers.get("HX-Request") == "true"


def toast(reponse, message: str, niveau: str = "succes", recharger: bool = False):
    """Notification affichee par base.html (evenement HTMX "toast")."""
    reponse["HX-Trigger"] = json.dumps(
        {"toast": {"message": message, "niveau": niveau, "recharger": recharger}})
    return reponse


def liste(requete):
    """Page d'accueil : les offres, filtrables."""
    aujourdhui = timezone.now().date()
    lot, filtres = filtrer(requete)

    # NULLS LAST : une offre sans echeance ne doit pas monopoliser le haut de
    # la liste, mais elle reste actionnable et ne peut pas etre reléguée.
    lot = lot.order_by("date_limite", "-date_ajout")

    pages = Paginator(lot.select_related("suivi"), PAR_PAGE)
    page = pages.get_page(requete.GET.get("page"))
    for offre in page:
        annoter(offre, aujourdhui)

    # Les compteurs portent sur la selection courante, pas sur toute la base :
    # ils doivent decrire ce que l'on regarde.
    compte = lot.aggregate(
        total=Count("id"),
        **{code: Count("id", filter=Q(secteur=code)) for code in SECTEURS_SUIVIS})

    # Le parametre de page est retire, sinon la pagination se fige sur la page
    # courante en changeant de filtre.
    parametres = requete.GET.copy()
    parametres.pop("page", None)

    # Le lieu n'a pas de selecteur dans le formulaire : il vient de la carte.
    # Il lui faut donc un moyen explicite de le retirer.
    sans_lieu = parametres.copy()
    sans_lieu.pop("lieu", None)

    return render(requete, "offres/liste.html", {
        "page": page,
        "filtres": filtres,
        "compte": compte,
        "sources": Offre.objects.values_list("source", flat=True)
                                .distinct().order_by("source"),
        "regions": geo.LIBELLES,
        "secteurs": SECTEURS,
        # Les compteurs sont apparies a leur libelle pour que le gabarit ne
        # code pas la liste des secteurs une seconde fois.
        "compteurs": [(code, libelle, compte[code]) for code, libelle in SECTEURS],
        "parametres": parametres.urlencode(),
        "parametres_sans_lieu": sans_lieu.urlencode(),
        "statuts": Suivi.STATUT_CHOICES,
    })


def detail(requete, offre_id):
    """Fiche d'une offre."""
    offre = get_object_or_404(Offre, pk=offre_id)
    annoter(offre)
    voisines = (Offre.objects.filter(source=offre.source, pertinent=True)
                .exclude(pk=offre.pk).order_by("date_limite")[:5])
    return render(requete, "offres/detail.html", {
        "offre": offre,
        "voisines": voisines,
        "suivi": Suivi.objects.filter(offre_id=offre.pk).first(),
        "statuts": Suivi.STATUT_CHOICES,
    })


def carte(requete):
    """Page portant la carte. Les points sont charges a part."""
    _, filtres = filtrer(requete)
    return render(requete, "offres/carte.html", {
        "filtres": filtres,
        "regions": geo.LIBELLES,
        "secteurs": SECTEURS,
        "sources": Offre.objects.values_list("source", flat=True)
                                .distinct().order_by("source"),
        "parametres": requete.GET.urlencode(),
    })


def agreger_par_lieu(lot) -> dict:
    """Les offres d'un queryset agregees par lieu, pour la carte.

    Un point par LIEU et non par offre : Madagascar en compte une centaine, et
    autant de marqueurs superposes au meme endroit ne se distingueraient pas.
    Le rayon dit le volume, l'infobulle donne le detail.

    Partagee entre la vue web et l'API : un tableau de bord externe doit voir
    la meme carte que l'ecran.
    """
    aujourdhui = timezone.now().date()

    par_lieu = {}
    sans_position = 0
    for offre in lot.only("id", "titre", "pays", "nature", "secteur",
                          "date_limite", "source"):
        position = geo.point(offre.pays)
        if position is None:
            sans_position += 1
            continue
        cle = (offre.pays or "").strip()
        entree = par_lieu.setdefault(cle, {
            "lieu": cle,
            "lat": position[0],
            "lon": position[1],
            "region": geo.LIBELLE[geo.region(offre.pays)],
            "total": 0, "marches": 0, "emplois": 0, "urgentes": 0,
            **{code: 0 for code in SECTEURS_SUIVIS},
            "exemples": [],
        })
        entree["total"] += 1
        if offre.nature == "marche":
            entree["marches"] += 1
        elif offre.nature == "emploi":
            entree["emplois"] += 1
        if offre.secteur in SECTEURS_SUIVIS:
            entree[offre.secteur] += 1
        if offre.date_limite and 0 <= (offre.date_limite - aujourdhui).days <= URGENT:
            entree["urgentes"] += 1
        # Trois titres suffisent a se faire une idee ; au-dela l'infobulle
        # deviendrait une page.
        if len(entree["exemples"]) < 3:
            entree["exemples"].append({"id": offre.id, "titre": offre.titre[:90]})

    points = sorted(par_lieu.values(), key=lambda p: -p["total"])
    return {
        "points": points,
        "total": sum(p["total"] for p in points),
        "sans_position": sans_position,
    }


def carte_points(requete):
    """Les offres agregees par lieu, en JSON, pour la carte.

    Repond aux memes filtres que la liste, pour que passer de l'une a l'autre
    ne change pas ce que l'on regarde.
    """
    lot, _ = filtrer(requete)
    return JsonResponse(agreger_par_lieu(lot),
                        json_dumps_params={"ensure_ascii": False})


@require_POST
def dater(requete, offre_id):
    """Saisit a la main l'echeance d'une offre que la source ne publie pas.

    La date est ecrite a DEUX endroits, a dessein :
      - suivi.echeance, avec l'auteur et l'instant : c'est la trace de la
        decision humaine, et elle survit a tout re-tri ;
      - offres.date_limite : c'est ce que lisent toutes les vues, l'API et
        le rapport, sans jointure. db.enregistrer ne l'ecrase plus par une
        valeur vide -- COALESCE -- donc elle survit aussi.
    """
    offre = get_object_or_404(Offre, pk=offre_id)
    brut = (requete.POST.get("echeance") or "").strip()
    try:
        echeance = date.fromisoformat(brut)
    except ValueError:
        if est_htmx(requete):
            return toast(HttpResponse(status=204), "Date illisible : attendu AAAA-MM-JJ.", "erreur")
        messages.error(requete, "Date illisible : attendu AAAA-MM-JJ.")
        return redirect("web-detail", offre_id=offre.pk)

    maintenant = timezone.now()
    Suivi.objects.update_or_create(
        offre_id=offre.pk,
        defaults={"echeance": echeance, "echeance_saisie_le": maintenant,
                  "decide_par": _auteur(requete)})
    Offre.objects.filter(pk=offre.pk).update(date_limite=echeance,
                                             date_maj=maintenant)
    if est_htmx(requete):
        offre.refresh_from_db()
        return toast(render(requete, "offres/_echeance.html", {"offre": annoter(offre)}),
                     f"Échéance enregistrée : {echeance:%d/%m/%Y}.")
    messages.success(requete, f"Échéance enregistrée : {echeance:%d/%m/%Y}.")

    # Retour vers la file si on en vient : la saisie s'enchaine.
    suivant = requete.POST.get("suivant") or ""
    if suivant == "file":
        return redirect("web-a-dater")
    return redirect("web-detail", offre_id=offre.pk)


@require_POST
def decider(requete, offre_id):
    """Pose ou change le statut commercial d'une offre.

    En POST seul : un GET qui modifie l'etat serait declenche par un
    prechargement de navigateur ou un robot d'indexation.
    """
    offre = get_object_or_404(Offre, pk=offre_id)
    # Sans statut (formulaire de note seul), le statut courant est conserve.
    actuel = Suivi.objects.filter(offre_id=offre.pk).values_list("statut", flat=True).first()
    statut = requete.POST.get("statut") or actuel or Suivi.A_ETUDIER
    if statut not in dict(Suivi.STATUT_CHOICES):
        if est_htmx(requete):
            return toast(HttpResponse(status=204), "Statut inconnu.", "erreur")
        messages.error(requete, "Statut inconnu.")
        return redirect("web-detail", offre_id=offre.pk)

    champs = {"statut": statut, "decide_par": _auteur(requete), "decide_par_cle": None}
    # Les boutons en 1 clic n'envoient pas de note : ne pas effacer l'existante.
    if "note" in requete.POST:
        champs["note"] = requete.POST["note"].strip()
    suivi, _ = Suivi.objects.update_or_create(offre_id=offre.pk, defaults=champs)
    libelle = dict(Suivi.STATUT_CHOICES)[statut]
    if est_htmx(requete):
        offre.suivi = suivi
        return toast(render(requete, "offres/_statut.html",
                            {"offre": offre, "statuts": Suivi.STATUT_CHOICES}),
                     f"Statut : {libelle}")
    messages.success(requete, f"Suivi mis à jour : {libelle}.")
    return redirect("web-detail", offre_id=offre.pk)


#: Sources tenues HORS de la file "a dater", avec la raison. Pas un reglage
#: de confort : chaque entree est un constat sur la source.
SOURCES_HORS_FILE = {
    # Ce sont des pages de PROJET, pas des avis de marche : l'API des projets
    # remonte tout l'historique malgache depuis 1980, sans description, et
    # son "closingdate" est la cloture du pret, pas une remise d'offres.
    # 26 entrees ont une echeance anterieure a l'an 2000. Les dater a la
    # main n'aurait aucun sens ; les vrais avis viennent de
    # banquemondiale-avis. Decision de l'exploitant, 11/09/2026.
    "banquemondiale",
}


def _file_a_dater(sources_incluses=None, sources_exclues=()):
    """Les offres a dater a la main, ordonnees : retenues, sans echeance.

    Ordre : Madagascar avant le reste, puis les secteurs ou Label Technology
    a un angle direct, puis les plus fraiches. Une offre s'y trouve jusqu'a ce
    qu'on lui donne une date ou qu'on la juge hors sujet.

    Le filtre de fraicheur ne s'applique qu'aux sources qui portent un repere
    d'age. Les projets Banque mondiale n'en ont aucun -- ni echeance, ni date
    de publication -- et se retrouveraient tous presumes clos le 19 septembre
    sans avoir ete regardes. Une source sans repere est donc servie entiere.
    """
    limite = timezone.now() - timedelta(days=PRESUMEE_CLOSE_JOURS)
    lot = (Offre.objects.filter(pertinent=True, nature="marche",
                                date_limite__isnull=True)
           .exclude(lien_etat__in=Offre.LIEN_FERME)
           .exclude(suivi__statut=Suivi.HORS_SUJET))
    if sources_incluses is not None:
        lot = lot.filter(source__in=sources_incluses)
    else:
        lot = lot.exclude(source__in=sources_exclues).filter(
            Q(date_publication__gte=limite.date())
            | Q(date_publication__isnull=True, date_ajout__gte=limite))

    offres = list(lot.select_related("suivi"))
    ordre_secteur = {"informatique": 0, "eau": 1, "environnement": 1,
                     "construction": 2, "agriculture": 2}
    for o in offres:
        o.region = geo.region(o.pays)
        o.region_libelle = geo.LIBELLE[o.region]
        o.publiee = o.date_publication or o.date_ajout.date()
    offres.sort(key=lambda o: (0 if o.region == geo.MADAGASCAR else 1,
                               ordre_secteur.get(o.secteur, 3),
                               -o.publiee.toordinal()))
    return offres


def _rendre_file(requete, offres, **contexte):
    pagination = Paginator(offres, 30)
    return render(requete, "offres/a_dater.html", {
        "page": pagination.get_page(requete.GET.get("page")),
        "total": len(offres),
        "madagascar": sum(1 for o in offres if o.region == geo.MADAGASCAR),
        **contexte,
    })


def a_dater(requete):
    """La file principale : toutes les sources sauf celles tenues a part."""
    return _rendre_file(requete, _file_a_dater(sources_exclues=SOURCES_HORS_FILE),
                        titre="Offres à dater",
                        sous_titre="Marchés retenus, récents, dont la source ne "
                                   "publie pas l'échéance dans sa page. Chacun "
                                   "attend qu'une personne lise le dossier et "
                                   "saisisse la date de remise — ou le juge hors "
                                   "sujet, ce qui le retire de la file.",
                        page_bm=True)


def a_dater_banque_mondiale(requete):
    """Les projets Banque mondiale, tenus a part.

    Ce sont des pages de PROJET et non des avis : leur "echeance" est la
    cloture du pret, leur description est vide, et l'API remonte l'historique
    malgache depuis 1980. Ils meritent un traitement a part, quand l'exploitant
    aura le temps -- pas de polluer la file des vrais avis.
    """
    return _rendre_file(requete, _file_a_dater(sources_incluses=["banquemondiale"]),
                        titre="Projets Banque mondiale à dater",
                        sous_titre="Pages de projet, pas des avis de marché : "
                                   "l'API des projets remonte tout l'historique "
                                   "malgache depuis 1980, sans description. "
                                   "Certains portent une échéance qui est la "
                                   "clôture du prêt. Les vrais avis viennent de "
                                   "banquemondiale-avis. À traiter plus tard, à "
                                   "part.",
                        page_bm=False)


def suivi(requete):
    """L'entonnoir commercial : ou en sont les offres qu'on a decide de suivre.

    Repond a la question que le tableau de bord ne posait pas -- un marche
    repere devient-il une candidature ? Tant que cette page reste vide, le
    systeme remonte des opportunites sans qu'on sache si elles servent.
    """
    lignes = (Suivi.objects.select_related("offre", "decide_par")
              .order_by("-maj_le"))

    filtre = requete.GET.get("statut", "")
    if filtre in dict(Suivi.STATUT_CHOICES):
        lignes = lignes.filter(statut=filtre)

    par_statut = dict(Suivi.objects.values_list("statut")
                      .annotate(n=Count("id")).values_list("statut", "n"))

    # L'entonnoir se lit en cumul : une offre gagnee est passee par la
    # candidature, meme si personne n'a clique sur l'etape intermediaire.
    etudiees = sum(par_statut.get(s, 0) for s in Suivi.ENTONNOIR)
    deposees = par_statut.get(Suivi.CANDIDATURE, 0) + par_statut.get(Suivi.GAGNE, 0) \
        + par_statut.get(Suivi.PERDU, 0)
    gagnees = par_statut.get(Suivi.GAGNE, 0)
    tranchees = deposees + par_statut.get(Suivi.HORS_SUJET, 0)

    def taux(part, total):
        return round(100 * part / total) if total else None

    pagination = Paginator(lignes, 40)
    return render(requete, "offres/suivi.html", {
        "page": pagination.get_page(requete.GET.get("page")),
        "statuts": Suivi.STATUT_CHOICES,
        "filtre": filtre,
        "par_statut": [(code, libelle, par_statut.get(code, 0))
                       for code, libelle in Suivi.STATUT_CHOICES],
        "entonnoir": [
            ("Suivies", etudiees + par_statut.get(Suivi.PERDU, 0)
             + par_statut.get(Suivi.HORS_SUJET, 0), None),
            ("Candidatures déposées", deposees, taux(deposees, tranchees)),
            ("Gagnées", gagnees, taux(gagnees, deposees)),
        ],
        # Le tri s'est trompe sur celles-la : c'est la mesure de sa precision,
        # rendue par des humains et non par le modele lui-meme.
        "hors_sujet": par_statut.get(Suivi.HORS_SUJET, 0),
        "total_suivi": sum(par_statut.values()),
    })


# ---------------------------------------------------------------- actions

def _panneau(requete, tache, suivi=False):
    """Panneau de progression. Tant que la tache tourne, il se recharge chaque seconde."""
    return render(requete, "offres/_taches.html", {"tache": tache, "suivi": suivi})


@require_POST
def lancer_tache(requete, nom):
    """Bouton de lancement : une tache de fond a la fois (voir services.taches.demarrer)."""
    if nom not in Tache.TYPES:
        return toast(HttpResponse(status=204), "Action inconnue.", "erreur")
    try:
        tache, _ = demarrer(nom)
    except DejaEnCours as exc:
        return toast(_panneau(requete, exc.tache, suivi=True),
                     f"Déjà en cours : {exc.tache.libelle}.", "info")
    except OSError as exc:
        return toast(HttpResponse(status=204), f"Lancement impossible : {exc}", "erreur")
    return toast(_panneau(requete, tache, suivi=True), f"{tache.libelle} : démarrage.")


def taches(requete):
    """Historique des taches, avec leur journal, et gestion des cles d'API."""
    Tache.active()  # clot au passage une tache dont le processus est mort
    return render(requete, "offres/taches.html", {
        "taches": Tache.objects.all()[:20],
        "types": [(nom, libelle, phases) for nom, (_, libelle, phases) in Tache.TYPES.items()],
        "cles": CleApi.objects.all(),
        "heure_auto": Parametres.charger().heure_collecte,
        "dernier_auto": Tache.objects.filter(automatique=True).first(),
    })


@require_POST
def creer_cle_api(requete):
    """Cree un jeton d'API et l'affiche UNE fois : seule son empreinte est gardee."""
    nom = (requete.POST.get("nom") or "").strip()[:80]
    contexte = {"cles": CleApi.objects.all()}
    if not nom or CleApi.objects.filter(nom=nom).exists():
        message = "Nom vide." if not nom else f"Une clé « {nom} » existe déjà."
        return toast(render(requete, "offres/_cles_api.html", contexte), message, "erreur")
    jeton = engendrer()
    CleApi.objects.create(nom=nom, empreinte=empreinte(jeton))
    return toast(render(requete, "offres/_cles_api.html", {**contexte, "jeton": jeton, "nom": nom}),
                 f"Clé « {nom} » créée.")


@require_POST
def revoquer_cle_api(requete, cle_id):
    CleApi.objects.filter(pk=cle_id, revoque_le__isnull=True).update(revoque_le=timezone.now())
    return toast(render(requete, "offres/_cles_api.html", {"cles": CleApi.objects.all()}),
                 "Clé révoquée.")


def parametres(requete):
    """Onglet Parametres : heure de la collecte automatique quotidienne."""
    reglages = Parametres.charger()
    if requete.method == "POST":
        try:
            heure = datetime.strptime((requete.POST.get("heure_collecte") or "").strip()[:5],
                                      "%H:%M").time()
        except ValueError:
            return toast(_bloc_parametres(requete, reglages),
                         "Heure illisible : attendu HH:MM.", "erreur")
        reglages.heure_collecte = heure
        reglages.save(update_fields=["heure_collecte"])
        message = f"Collecte automatique réglée à {heure:%H:%M}."
        if est_htmx(requete):
            return toast(_bloc_parametres(requete, reglages), message)
        messages.success(requete, message)
        return redirect("web-parametres")
    return render(requete, "offres/parametres.html", _contexte_parametres(reglages))


def _contexte_parametres(reglages):
    return {"reglages": reglages,
            "prochain": prochaine_execution(timezone.localtime(), reglages.heure_collecte),
            "dernier_auto": Tache.objects.filter(automatique=True).first()}


def _bloc_parametres(requete, reglages):
    return render(requete, "offres/_parametres.html", _contexte_parametres(reglages))


def etat_taches(requete):
    """Interroge par le panneau. `suivi` = le panneau observait deja cette tache :
    sa fin declenche alors une notification et l'affichage du bilan."""
    tache = Tache.active()
    if tache:
        return _panneau(requete, tache, suivi=True)
    suivie = requete.GET.get("suivi")
    if suivie:
        fini = Tache.objects.filter(pk=suivie).first()
        if fini:
            reponse = _panneau(requete, fini)
            if fini.statut == Tache.ECHEC:
                return toast(reponse, f"{fini.libelle} : échec.", "erreur")
            return toast(reponse, f"{fini.libelle} : terminé.")
    return HttpResponse("")


CHAMPS_EXPORT = ["id", "source", "titre", "organisation", "pays", "date_publication",
                 "date_limite", "nature", "secteur", "categorie", "raison", "lien",
                 "lien_etat", "suivi__statut"]


def exporter(requete):
    """La selection courante (memes filtres que la liste) en CSV ou JSON."""
    lot, _ = filtrer(requete)
    lignes = lot.order_by("date_limite", "-date_ajout").values(*CHAMPS_EXPORT)
    nom = f"offres-{timezone.now():%Y%m%d}"
    if requete.GET.get("format") == "json":
        reponse = JsonResponse(list(lignes), safe=False, json_dumps_params={"ensure_ascii": False})
        reponse["Content-Disposition"] = f'attachment; filename="{nom}.json"'
        return reponse
    reponse = HttpResponse(content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = f'attachment; filename="{nom}.csv"'
    reponse.write("\ufeff")  # BOM : Excel lit alors l'UTF-8 correctement
    ecrivain = csv.DictWriter(reponse, fieldnames=CHAMPS_EXPORT)
    ecrivain.writeheader()
    ecrivain.writerows(lignes)
    return reponse


def recapitulatif(requete):
    """Texte du recapitulatif de la selection courante, pour le presse-papier."""
    lot, _ = filtrer(requete)
    offres = list(lot.order_by("date_limite", "-date_ajout")[:100])
    return HttpResponse(NotificationService.construire_corps(offres),
                        content_type="text/plain; charset=utf-8")
