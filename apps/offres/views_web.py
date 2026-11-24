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
import re
from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db.models import Count, Max, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .auth import empreinte, engendrer
from .comptes import admin_requis
from .models import (PRESUMEE_CLOSE_JOURS, CleApi, Offre, Parametres, Pays, Secteur,
                     Suivi, Tache)
from .scrapers import REGISTRE_SCRAPERS
from .services import geo
from .services.notification import NotificationService
from .services.taches import DejaEnCours, demarrer, prochaine_execution, reprendre

from .services.classifier import RuleBasedClassifier
from .services.taxonomie import code_pays, code_secteur

# Secteurs connus pour guider le tri ; le catalogue et les valeurs déjà
# présentes en base restent disponibles sans modifier le code.
SECTEURS = {code: code.replace("_", " ").capitalize()
            for code in RuleBasedClassifier.SECTEURS}
SECTEURS_SUIVIS = list(SECTEURS)


def secteurs_disponibles():
    libelles = dict(SECTEURS)
    libelles.update(Secteur.objects.filter(actif=True).values_list("code", "nom"))
    inactifs = set(Secteur.objects.filter(actif=False).values_list("code", flat=True))
    codes = set(Offre.objects.exclude(secteur__isnull=True).exclude(secteur="")
                .values_list("secteur", flat=True))
    # Expose aussi les secteurs connus sans attendre leur première offre.
    codes.update(Secteur.objects.filter(actif=True).values_list("code", flat=True))
    codes.update(SECTEURS_SUIVIS)
    return sorted(((code, libelles.get(code, code.replace("_", " ").capitalize()))
                   for code in codes if code != "autre" and code not in inactifs),
                  key=lambda x: (x[1].casefold(), x[0]))


def pays_disponibles():
    """Pays et libellés de lieu actifs dans le catalogue des filtres."""
    return list(Pays.objects.filter(actif=True).values_list("code", "nom"))

#: Offres par page. Au-dela, la page devient longue a parcourir sans gagner
#: en utilite : on vient ici pour reperer, pas pour tout lire.
PAR_PAGE = 27  # multiple de 3 : la grille de cartes tombe juste

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

    etat = requete.GET.get("etat") or "toutes"
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
    elif etat == "cloturees":
        # Offres dont l'echeance est passee ou que la source a retirees / closes.
        lot = lot.filter(pertinent=True).filter(
            Q(date_limite__lt=aujourdhui) | ferme)
    elif etat == "toutes":
        # La vue generale garde les offres consultees, sans noyer la liste
        # avec celles deja expirees ou retirees. Le filtre "cloturees" les
        # rend accessibles a la demande.
        lot = lot.exclude(Q(date_limite__lt=aujourdhui) | ferme)
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

    nature = requete.GET.get("nature") or ""
    if nature in ("marche", "emploi"):
        lot = lot.filter(nature=nature)
    elif nature == "inconnue":
        lot = lot.filter(nature__isnull=True)

    # Filtre sur toute valeur connue en base, y compris les nouveaux secteurs.
    secteur = requete.GET.get("secteur") or ""
    if secteur in {code for code, _ in secteurs_disponibles()}:
        lot = lot.filter(secteur=secteur)

    pays = requete.GET.get("pays") or ""
    pays_actifs = {code for code, _ in pays_disponibles()}
    if pays in pays_actifs:
        valeurs_pays = [valeur for valeur in
                        Offre.objects.exclude(pays__isnull=True).exclude(pays="")
                        .values_list("pays", flat=True).distinct()
                        if code_pays(valeur) == pays]
        lot = lot.filter(pays__in=valeurs_pays) if valeurs_pays else lot.none()
    elif pays and Pays.objects.filter(code=pays).exists():
        # Une URL conservée après désactivation ne doit pas revenir à toute la base.
        lot = lot.none()

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

    recherche = (requete.GET.get("q") or "").strip()
    if recherche:
        lot = lot.filter(Q(titre__icontains=recherche)
                         | Q(organisation__icontains=recherche)
                         | Q(categorie__icontains=recherche))

    # La période porte sur la date limite de l'offre. Les bornes sont
    # inclusives ; une saisie invalide reste visible dans le formulaire mais
    # n'est pas envoyée à PostgreSQL.
    date_de = (requete.GET.get("date_de") or "").strip()
    date_a = (requete.GET.get("date_a") or "").strip()
    try:
        date_de_valide = date.fromisoformat(date_de) if date_de else None
    except ValueError:
        date_de_valide = None
    try:
        date_a_valide = date.fromisoformat(date_a) if date_a else None
    except ValueError:
        date_a_valide = None
    if date_de_valide:
        lot = lot.filter(date_limite__gte=date_de_valide)
    if date_a_valide:
        lot = lot.filter(date_limite__lte=date_a_valide)

    filtres = {"etat": etat, "nature": nature, "secteur": secteur, "pays": pays,
               "region": demandee, "lieu": lieu, "q": recherche, "date_de": date_de, "date_a": date_a}
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


def libelles_secteurs() -> dict:
    """Code -> nom affiche, secteurs desactives compris (une offre peut encore en porter un)."""
    return {**SECTEURS, **dict(Secteur.objects.values_list("code", "nom"))}


def titre_lisible(titre: str) -> str:
    """Un titre ecrit TOUT EN MAJUSCULES par sa source passe en casse de phrase.

    Les references (mots porteurs d'un chiffre : "RFP-2026/014") restent telles
    quelles. shortcut: les sigles sans chiffre ("UNICEF") passent en minuscules ;
    tenir une liste de sigles si cela gene a l'usage.
    """
    lettres = [c for c in titre or "" if c.isalpha()]
    if len(lettres) < 8 or sum(c.isupper() for c in lettres) < 0.8 * len(lettres):
        return titre
    texte = " ".join(m if any(c.isdigit() for c in m) else m.lower() for m in titre.split(" "))
    return texte[:1].upper() + texte[1:]


#: Nom lisible de chaque source ("Grants.gov (Etats-Unis)" plutot que "grants_gov").
NOMS_SOURCES = {s.source_key: s.nom for s in REGISTRE_SCRAPERS}


def annoter(offre, aujourdhui=None, libelles=None):
    """Attributs d'affichage : etat d'echeance, region, libelle du secteur, source."""
    offre.source_nom = NOMS_SOURCES.get(offre.source) or offre.source
    offre.titre_lisible = titre_lisible(offre.titre)
    offre.etat_echeance, offre.jours = urgence(offre, aujourdhui or timezone.now().date())
    code = offre.secteur or ""
    offre.secteur_libelle = (libelles or libelles_secteurs()).get(
        code, code.replace("_", " ").capitalize())
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
    libelles = libelles_secteurs()
    for offre in page:
        annoter(offre, aujourdhui, libelles)

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
    # Les onglets d'affichage changent l'etat et gardent les autres filtres.
    sans_etat = parametres.copy()
    sans_etat.pop("etat", None)

    return render(requete, "offres/liste.html", {
        "page": page,
        "filtres": filtres,
        "compte": compte,
        "regions": geo.LIBELLES,
        "secteurs": secteurs_disponibles(),
        "pays": pays_disponibles(),
        # Les compteurs sont apparies a leur libelle pour que le gabarit ne
        # code pas la liste des secteurs une seconde fois.
        "compteurs": [(code, libelle, lot.filter(secteur=code).count())
                      for code, libelle in secteurs_disponibles()],
        "parametres": parametres.urlencode(),
        "parametres_sans_lieu": sans_lieu.urlencode(),
        "parametres_sans_etat": sans_etat.urlencode(),
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


@login_not_required
def carte(requete):
    """Page portant la carte. Les points sont charges a part.

    Sans connexion : la carte publique, sans filtres, nourrie par l'API publique."""
    if not requete.user.is_authenticated:
        return render(requete, "offres/carte_publique.html", {"parametres": ""})
    _, filtres = filtrer(requete)
    return render(requete, "offres/carte.html", {
        "filtres": filtres,
        "regions": geo.LIBELLES,
        "secteurs": secteurs_disponibles(),
        "pays": pays_disponibles(),
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
    secteurs = [code for code, _ in secteurs_disponibles()]

    par_lieu = {}
    sans_position = 0
    # Des tuples plutot que des objets Offre : 4x moins cher sur des milliers de lignes.
    for pk, titre, pays, nature, secteur, date_limite in lot.values_list(
            "id", "titre", "pays", "nature", "secteur", "date_limite"):
        position = geo.point(pays)
        if position is None:
            sans_position += 1
            continue
        cle = (pays or "").strip()
        entree = par_lieu.get(cle)
        if entree is None:
            entree = par_lieu[cle] = {
                "lieu": cle,
                "lat": position[0],
                "lon": position[1],
                "region": geo.LIBELLE[geo.region(pays)],
                "total": 0, "marches": 0, "emplois": 0, "urgentes": 0,
                **{code: 0 for code in secteurs},
                "exemples": [],
            }
        entree["total"] += 1
        if nature == "marche":
            entree["marches"] += 1
        elif nature == "emploi":
            entree["emplois"] += 1
        if secteur in secteurs:
            entree[secteur] += 1
        if date_limite and 0 <= (date_limite - aujourdhui).days <= URGENT:
            entree["urgentes"] += 1
        # Trois titres suffisent a se faire une idee ; au-dela l'infobulle
        # deviendrait une page.
        if len(entree["exemples"]) < 3:
            entree["exemples"].append({"id": pk, "titre": titre[:90]})

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


@admin_requis
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


@admin_requis
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


@admin_requis
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


@admin_requis
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


@admin_requis
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


@admin_requis
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


@admin_requis
def taches(requete):
    """Historique des taches, avec leur journal, et gestion des cles d'API."""
    Tache.active()  # clot au passage une tache dont le processus est mort
    return render(requete, "offres/taches.html", {
        "taches": Tache.objects.all()[:20],
        "types": [(nom, libelle, phases) for nom, (_, libelle, phases) in Tache.TYPES.items()],
        "cles": CleApi.objects.all(),
        "intervalle_auto": Parametres.charger().intervalle_collecte,
        "reglages": Parametres.charger(),
        "nb_actives": Tache.objects.filter(statut__in=(Tache.EN_COURS, *Tache.EN_ATTENTE)).count(),
        "dernier_auto": Tache.objects.filter(automatique=True).first(),
        "nb_sources": len(REGISTRE_SCRAPERS),
    })


@admin_requis
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


@admin_requis
@require_POST
def revoquer_cle_api(requete, cle_id):
    CleApi.objects.filter(pk=cle_id, revoque_le__isnull=True).update(revoque_le=timezone.now())
    return toast(render(requete, "offres/_cles_api.html", {"cles": CleApi.objects.all()}),
                 "Clé révoquée.")


@admin_requis
def parametres(requete):
    """Onglet Paramètres : fréquence de la collecte automatique."""
    reglages = Parametres.charger()
    if requete.method == "POST":
        try:
            intervalle = int(requete.POST.get("intervalle_collecte", ""))
            if not 1 <= intervalle <= 24:
                raise ValueError
        except (TypeError, ValueError):
            return toast(_bloc_parametres(requete, reglages),
                         "Intervalle invalide : choisissez une valeur de 1 à 24 heures.", "erreur")
        reglages.intervalle_collecte = intervalle
        champs = ["intervalle_collecte"]
        message = f"Collecte automatique réglée toutes les {intervalle} heure(s)."
        if requete.POST.get("heure_nuit"):
            try:
                reglages.heure_nuit = datetime.strptime(requete.POST["heure_nuit"], "%H:%M").time()
            except ValueError:
                return toast(_bloc_parametres(requete, reglages),
                             "Heure de nuit invalide : attendu HH:MM.", "erreur")
            champs.append("heure_nuit")
            message += f" Organisation de nuit à {reglages.heure_nuit:%H:%M}."
        reglages.save(update_fields=champs)
        if est_htmx(requete):
            return toast(_bloc_parametres(requete, reglages), message)
        messages.success(requete, message)
        return redirect("web-parametres")
    return render(requete, "offres/parametres.html", {
        **_contexte_parametres(reglages), **_contexte_secteurs(),
        **_contexte_pays(), **_contexte_email(reglages), **_contexte_pertinence(reglages),
        **_contexte_sources(),
    })


def _contexte_sources():
    """Les sources collectées, dans l'ordre de la collecte, avec ce qu'elles ont rapporté."""
    bilan = {l["source"]: l for l in Offre.objects.values("source")
             .annotate(total=Count("id"), derniere=Max("date_ajout"))}
    return {"lignes_sources": [
        {"scraper": s, "domaine": s.site.split("/")[2] if "//" in s.site else s.site,
         "total": bilan.get(s.source_key, {}).get("total", 0),
         "derniere": bilan.get(s.source_key, {}).get("derniere")}
        for s in REGISTRE_SCRAPERS]}


def _contexte_parametres(reglages):
    return {"reglages": reglages,
            "prochain": prochaine_execution(timezone.localtime(), reglages.intervalle_collecte),
            "dernier_auto": Tache.objects.filter(automatique=True).exclude(nom="nuit").first(),
            "derniere_nuit": Tache.objects.filter(nom="nuit").first()}


def _bloc_parametres(requete, reglages):
    return render(requete, "offres/_parametres.html", _contexte_parametres(reglages))


def _contexte_email(reglages):
    if reglages.smtp_hote:
        source = "ecran"
    else:
        source = "env" if settings.SMTP_HOST else "console"
    return {"reglages": reglages, "email_source": source, "smtp_env": settings.SMTP_HOST,
            "destinataires_effectifs": reglages.liste_destinataires() or settings.NOTIFY_TO}


@admin_requis
@require_POST
def parametres_email(requete):
    """Serveur SMTP et destinataires du récapitulatif, saisis à l'écran.

    Le mot de passe n'est jamais renvoyé à la page : champ vide = inchangé.
    Il est effacé si le serveur ou l'utilisateur change sans être ressaisi,
    pour qu'il ne parte pas vers un autre serveur que celui pour lequel il a été donné.
    """
    reglages = Parametres.charger()
    p = requete.POST
    hote = p.get("smtp_hote", "").strip()
    utilisateur = p.get("smtp_utilisateur", "").strip()
    mot_de_passe = p.get("smtp_mot_de_passe", "")
    securite = p.get("smtp_securite", "tls")
    destinataires = [a for a in re.split(r"[,;\s]+", p.get("destinataires", "")) if a]

    erreurs = []
    if securite not in dict(Parametres.SECURITES_SMTP):
        erreurs.append("sécurité inconnue")
    if re.search(r"[\s/]", hote) or len(hote) > 255:
        erreurs.append("serveur illisible (ex. smtp.gmail.com)")
    try:
        port = int(p.get("smtp_port") or {"ssl": 465, "aucune": 25}.get(securite, 587))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        erreurs.append("port invalide (1 à 65535)")
    invalides = []
    for adresse in destinataires:
        try:
            validate_email(adresse)
        except ValidationError:
            invalides.append(adresse)
    if invalides:
        erreurs.append("adresse invalide : " + ", ".join(invalides))
    if erreurs:
        # 204 : le formulaire garde la saisie pour qu'on la corrige.
        return toast(HttpResponse(status=204), "Email non enregistré : " + " ; ".join(erreurs) + ".", "erreur")

    efface = False
    if not hote:
        # Serveur vide : retour au .env, rien d'inutile ne reste en base.
        utilisateur, mot_de_passe = "", ""
        reglages.smtp_mot_de_passe = ""
    elif mot_de_passe:
        reglages.smtp_mot_de_passe = mot_de_passe
    elif (hote, utilisateur) != (reglages.smtp_hote, reglages.smtp_utilisateur):
        efface = bool(reglages.smtp_mot_de_passe)
        reglages.smtp_mot_de_passe = ""
    reglages.smtp_hote, reglages.smtp_port, reglages.smtp_securite = hote, port, securite
    reglages.smtp_utilisateur = utilisateur
    reglages.destinataires = ", ".join(destinataires)
    reglages.save(update_fields=["smtp_hote", "smtp_port", "smtp_securite", "smtp_utilisateur",
                                 "smtp_mot_de_passe", "destinataires"])

    message = "Configuration email enregistrée."
    if efface:
        message += " Le serveur ou l'utilisateur a changé : saisissez à nouveau le mot de passe."
    if est_htmx(requete):
        return toast(render(requete, "offres/_email.html", _contexte_email(reglages)),
                     message, "info" if efface else "succes")
    messages.success(requete, message)
    return redirect(reverse("web-parametres") + "#email")


CRITERES_SCORE = [("competences", "Compétences"), ("domaine", "Domaine (secteur)"),
                  ("categorie", "Catégorie"), ("localisation", "Localisation"),
                  ("mots_cles", "Mots-clés")]


def _contexte_pertinence(reglages):
    poids = reglages.ponderation()
    return {"criteres_score": [(code, libelle, poids[code]) for code, libelle in CRITERES_SCORE],
            "total_poids": sum(poids.values())}


@admin_requis
@require_POST
def parametres_pertinence(requete):
    """Pondération du score de correspondance offre / profil."""
    reglages = Parametres.charger()
    try:
        poids = {code: int(requete.POST.get(code, "")) for code, _ in CRITERES_SCORE}
        if not all(0 <= v <= 100 for v in poids.values()) or not sum(poids.values()):
            raise ValueError
    except ValueError:
        return toast(HttpResponse(status=204),
                     "Poids invalides : des entiers de 0 à 100, pas tous nuls.", "erreur")
    reglages.poids = poids
    reglages.save(update_fields=["poids"])
    return toast(render(requete, "offres/_pertinence.html", _contexte_pertinence(reglages)),
                 "Pondération enregistrée.")


@admin_requis
@require_POST
def tester_email(requete):
    """Envoie un email de test avec la configuration enregistrée."""
    try:
        destinataires = NotificationService.envoyer(
            "Veille appels d'offres : email de test",
            "Cet email confirme que l'envoi du récapitulatif fonctionne.")
    except Exception as exc:
        return toast(HttpResponse(status=204), f"Échec de l'envoi : {exc}", "erreur")
    if not destinataires:
        return toast(HttpResponse(status=204), "Aucun destinataire : ajoutez-en au moins un.", "erreur")
    if _contexte_email(Parametres.charger())["email_source"] == "console":
        return toast(HttpResponse(status=204),
                     "Aucun serveur SMTP : l'email de test est seulement écrit dans le journal du serveur.", "info")
    return toast(HttpResponse(status=204), f"Email de test envoyé à {', '.join(destinataires)}.")


def _contexte_secteurs():
    comptes = dict(Offre.objects.exclude(secteur__isnull=True).exclude(secteur="")
                   .values("secteur").annotate(total=Count("id"))
                   .values_list("secteur", "total"))
    lignes = [{"secteur": secteur, "nombre_offres": comptes.get(secteur.code, 0)}
              for secteur in Secteur.objects.all()]
    return {"lignes_secteurs": lignes}


def _bloc_secteurs(requete):
    return render(requete, "offres/_secteurs.html", _contexte_secteurs())


def _contexte_pays():
    comptes = {}
    lieux = (Offre.objects.exclude(pays__isnull=True).exclude(pays="")
             .values("pays").annotate(total=Count("id")))
    for ligne in lieux:
        code = code_pays(ligne["pays"])
        comptes[code] = comptes.get(code, 0) + ligne["total"]
    lignes = [{"pays": pays, "nombre_offres": comptes.get(pays.code, 0)}
              for pays in Pays.objects.all()]
    return {"lignes_pays": lignes}


def _bloc_pays(requete):
    return render(requete, "offres/_pays.html", _contexte_pays())


@admin_requis
@require_POST
def creer_pays(requete):
    nom = (requete.POST.get("nom") or "").strip()[:100]
    code = code_pays(nom)
    if not nom or not code:
        return toast(_bloc_pays(requete), "Nom de pays invalide.", "erreur")
    pays, cree = Pays.objects.get_or_create(code=code, defaults={"nom": nom})
    if not cree and pays.actif:
        return toast(_bloc_pays(requete), f"« {pays.nom} » existe déjà.", "erreur")
    if not cree:
        pays.nom = nom
        pays.actif = True
        pays.save(update_fields=["nom", "actif"])
    return toast(_bloc_pays(requete), f"Pays « {nom} » ajouté au catalogue.")


@admin_requis
@require_POST
def modifier_pays(requete, pays_id):
    pays = get_object_or_404(Pays, pk=pays_id)
    nom = (requete.POST.get("nom") or "").strip()[:100]
    if not nom:
        return toast(_bloc_pays(requete), "Le nom du pays ne peut pas être vide.", "erreur")
    pays.nom = nom
    pays.save(update_fields=["nom"])
    return toast(_bloc_pays(requete), f"Libellé du pays modifié en « {nom} »."
                 " Les lieux déjà enregistrés restent inchangés.")


@admin_requis
@require_POST
def basculer_pays(requete, pays_id):
    pays = get_object_or_404(Pays, pk=pays_id)
    pays.actif = not pays.actif
    pays.save(update_fields=["actif"])
    message = (f"Pays « {pays.nom} » activé dans les filtres."
               if pays.actif else
               f"Pays « {pays.nom} » désactivé des filtres; les offres sont conservées.")
    return toast(_bloc_pays(requete), message)


@admin_requis
@require_POST
def supprimer_pays(requete, pays_id):
    pays = get_object_or_404(Pays, pk=pays_id)
    pays.actif = False
    pays.save(update_fields=["actif"])
    return toast(_bloc_pays(requete),
                 f"Pays « {pays.nom} » retiré des choix actifs; les offres sont conservées.")


@admin_requis
@require_POST
def creer_secteur(requete):
    nom = (requete.POST.get("nom") or "").strip()[:100]
    code = code_secteur(nom)[:100].rstrip("_")
    if not nom or not code or code == "autre":
        return toast(_bloc_secteurs(requete),
                     "Nom de secteur invalide. Choisissez un nom descriptif.", "erreur")

    secteur, cree = Secteur.objects.get_or_create(
        code=code, defaults={"nom": nom, "actif": True})
    if not cree and secteur.actif:
        return toast(_bloc_secteurs(requete),
                     f"Le secteur « {secteur.nom} » existe déjà.", "erreur")
    if not cree:
        secteur.nom = nom
        secteur.actif = True
        secteur.save(update_fields=["nom", "actif"])
    return toast(_bloc_secteurs(requete), f"Secteur « {nom} » ajouté au catalogue.")


@admin_requis
@require_POST
def modifier_secteur(requete, secteur_id):
    secteur = get_object_or_404(Secteur, pk=secteur_id)
    nom = (requete.POST.get("nom") or "").strip()[:100]
    if not nom:
        return toast(_bloc_secteurs(requete), "Le nom du secteur ne peut pas être vide.", "erreur")
    secteur.nom = nom
    secteur.save(update_fields=["nom"])

    # Met aussi à jour la catégorie lisible des offres déjà classées.
    tampon = []
    for offre in Offre.objects.filter(secteur=secteur.code).only("id", "nature"):
        offre.categorie = f"{nom} - {(offre.nature or 'marche').capitalize()}"
        tampon.append(offre)
        if len(tampon) >= 500:
            Offre.objects.bulk_update(tampon, ["categorie"], batch_size=500)
            tampon = []
    if tampon:
        Offre.objects.bulk_update(tampon, ["categorie"], batch_size=500)
    return toast(_bloc_secteurs(requete), f"Secteur renommé « {nom} ».")


@admin_requis
@require_POST
def basculer_secteur(requete, secteur_id):
    secteur = get_object_or_404(Secteur, pk=secteur_id)
    secteur.actif = not secteur.actif
    secteur.save(update_fields=["actif"])
    message = (f"Secteur « {secteur.nom} » activé dans les filtres et le tri."
               if secteur.actif else
               f"Secteur « {secteur.nom} » désactivé; les offres existantes sont conservées.")
    return toast(_bloc_secteurs(requete), message)


@admin_requis
@require_POST
def supprimer_secteur(requete, secteur_id):
    secteur = get_object_or_404(Secteur, pk=secteur_id)
    utilise = Offre.objects.filter(secteur=secteur.code).exists()
    # Archivage plutôt que suppression physique : l'IA ne le reproposera pas,
    # et l'utilisateur peut restaurer un code sans perdre l'historique.
    secteur.actif = False
    secteur.save(update_fields=["actif"])
    if utilise:
        message = (f"Secteur « {secteur.nom} » supprimé des choix actifs. "
                   "Les offres déjà classées sont conservées; il peut être réactivé.")
    else:
        message = f"Secteur « {secteur.nom} » retiré du catalogue; il peut être réactivé."
    return toast(_bloc_secteurs(requete), message)


def _apres_action(requete, reponse, message, niveau="succes"):
    """Toast ; sur la page Taches, l'historique est recharge pour refleter l'action."""
    sur_taches = "/taches/" in requete.headers.get("HX-Current-URL", "")
    return toast(reponse, message, niveau, recharger=sur_taches)


def _reprendre(requete, tache):
    try:
        lance = reprendre(tache, manuel=True)
    except DejaEnCours as exc:
        return toast(_panneau(requete, exc.tache, suivi=True),
                     f"Déjà en cours : {exc.tache.libelle}.", "info")
    except OSError as exc:
        return toast(HttpResponse(status=204), f"Reprise impossible : {exc}", "erreur")
    return _apres_action(requete, _panneau(requete, lance[0], suivi=True),
                         f"{tache.libelle} : reprise.")


@admin_requis
@require_POST
def action_tache(requete, tache_id, action):
    """Suspendre, annuler ou reprendre UNE tache."""
    tache = get_object_or_404(Tache, pk=tache_id)
    lot = Tache.objects.filter(pk=tache.pk)
    if action == "reprendre" and tache.statut in Tache.EN_ATTENTE:
        return _reprendre(requete, tache)
    if action == "suspendre" and tache.statut == Tache.EN_COURS:
        Tache.arreter(lot, Tache.SUSPENDUE,
                      f"Suspendue pendant « {tache.etape} » : reprendra au même point.")
        message = f"{tache.libelle} : suspension (effective sous 5 s)."
    elif action == "annuler" and tache.statut in (Tache.EN_COURS, *Tache.EN_ATTENTE):
        Tache.arreter(lot, Tache.ANNULEE, f"Annulée pendant « {tache.etape} ».")
        message = f"{tache.libelle} : annulation (effective sous 5 s)."
    else:
        return toast(HttpResponse(status=204),
                     f"Impossible de {action} une tâche {tache.get_statut_display().lower()}.", "erreur")
    tache.refresh_from_db()
    return _apres_action(requete, _panneau(requete, tache), message)


@admin_requis
@require_POST
def action_globale(requete, action):
    """Pour toutes les taches : tout suspendre (automatismes compris), tout reprendre, tout annuler."""
    reglages = Parametres.charger()
    actives = Tache.objects.filter(statut__in=(Tache.EN_COURS, *Tache.EN_ATTENTE))
    if action == "suspendre":
        Parametres.objects.filter(pk=reglages.pk).update(automatismes_suspendus=True)
        n = Tache.arreter(actives.exclude(statut=Tache.SUSPENDUE), Tache.SUSPENDUE,
                          "Suspendue (tout suspendre) : reprendra au même point.")
        message = f"Tout est suspendu : {n} tâche(s), collecte automatique et reprises en pause."
    elif action == "annuler":
        n = Tache.arreter(actives, Tache.ANNULEE, "Annulée (tout annuler).")
        message = f"{n} tâche(s) annulée(s)."
    elif action == "reprendre":
        Parametres.objects.filter(pk=reglages.pk).update(automatismes_suspendus=False)
        suspendues = list(Tache.objects.filter(statut=Tache.SUSPENDUE).order_by("debut"))
        # Une a la fois : la premiere tout de suite, les suivantes par le planificateur.
        Tache.objects.filter(pk__in=[t.pk for t in suspendues[1:]]).update(statut=Tache.INTERROMPUE)
        if suspendues:
            return _reprendre(requete, suspendues[0])
        message = "Automatismes réactivés."
    else:
        return toast(HttpResponse(status=204), "Action inconnue.", "erreur")
    return _apres_action(requete, etat_taches(requete), message)


@admin_requis
def etat_taches(requete):
    """Interroge par le panneau. `suivi` = le panneau observait deja cette tache :
    sa fin declenche alors une notification et l'affichage du bilan."""
    tache = Tache.active()
    if tache:
        return _panneau(requete, tache, suivi=True)
    en_attente = (Tache.a_reprendre()
                  or Tache.objects.filter(statut=Tache.SUSPENDUE).order_by("-debut").first())
    if en_attente:
        return _panneau(requete, en_attente)
    suivie = requete.GET.get("suivi")
    if suivie:
        fini = Tache.objects.filter(pk=suivie).first()
        if fini:
            reponse = _panneau(requete, fini)
            if fini.statut == Tache.ECHEC:
                return toast(reponse, f"{fini.libelle} : échec.", "erreur")
            if fini.statut == Tache.ANNULEE:
                return toast(reponse, f"{fini.libelle} : annulée.", "info")
            return toast(reponse, f"{fini.libelle} : terminé.")
    if Parametres.charger().automatismes_suspendus:
        return render(requete, "offres/_taches.html", {"automatismes_suspendus": True})
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
