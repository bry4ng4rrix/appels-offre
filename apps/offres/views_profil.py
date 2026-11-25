"""Pages du compte : profil (sections A à E), CV, suggestions, notifications.

Chaque section du profil s'enregistre à part : une erreur dans l'une ne fait
pas perdre la saisie des autres. Les fichiers (CV, photo) ne sortent que par
`cv` et `photo`, qui vérifient que le demandeur est le propriétaire ou un admin.
"""

import os
import re

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .comptes import admin_requis, est_admin
from .fichiers import TYPES_PHOTO
from .forms import (CVForm, DomainesForm, InfosPersonnellesForm, InfosProForm, PlanForm,
                    PreferencesForm)
from .models import Abonnement, Consultation, Notification, Plan, Preferences, Profil
from .services import geo
from .services.correspondance import suggestions
from .views_web import PAR_PAGE, annoter, libelles_secteurs

ONGLETS = ["perso", "pro", "domaines", "cv", "preferences"]
FORMULAIRES = {"perso": InfosPersonnellesForm, "pro": InfosProForm,
               "domaines": DomainesForm, "preferences": PreferencesForm}


def _avatar(user, profil):
    if profil.photo:
        return reverse("web-profil-photo", args=[user.pk])
    compte = user.socialaccount_set.first()
    return compte.get_avatar_url() if compte else ""


def profil(requete):
    user = requete.user
    fiche, prefs = Profil.de(user), Preferences.de(user)
    instances = {"perso": fiche, "pro": fiche, "domaines": fiche, "preferences": prefs}
    # prefix : « pays » existe dans deux sections, les id HTML doivent differer.
    formulaires = {nom: cls(instance=instances[nom], prefix=nom) for nom, cls in FORMULAIRES.items()}
    form_cv, onglet = CVForm(prefix="cv"), ""

    if requete.method == "POST":
        section = requete.POST.get("section", "")
        suivant = requete.POST.get("suivant", "")
        if section in FORMULAIRES:
            form = FORMULAIRES[section](requete.POST, requete.FILES, instance=instances[section],
                                        prefix=section)
            if form.is_valid():
                form.save()
                messages.success(requete, "Profil enregistré.")
                return _apres(section, suivant)
            formulaires[section], onglet = form, section
        elif section == "cv":
            form_cv = CVForm(requete.POST, requete.FILES, prefix="cv")
            if form_cv.is_valid():
                deposer_cv(fiche, form_cv.cleaned_data["fichier"])
                messages.success(requete, "CV enregistré.")
                return _apres("cv", suivant)
            onglet = "cv"
        elif section == "cv-supprimer":
            if supprimer_cv(fiche):
                messages.success(requete, "CV supprimé.")
            return _apres("cv", "")
        else:
            return HttpResponseBadRequest("Section inconnue.")

    return render(requete, "offres/profil.html", {
        "fiche": fiche, "formulaires": formulaires, "form_cv": form_cv,
        "onglet": onglet, "avatar": _avatar(user, fiche), "completion": fiche.completion(),
        "bienvenue": "bienvenue" in requete.GET,
    }, status=400 if onglet else 200)


def deposer_cv(fiche, fichier):
    """Remplace le CV du profil (l'ancien fichier est effacé du disque)."""
    if fiche.cv:
        fiche.cv.delete(save=False)
    fiche.cv = fichier
    fiche.cv_nom = os.path.basename(fichier.name)[:255]
    fiche.cv_depose_le = timezone.now()
    fiche.save()


def supprimer_cv(fiche) -> bool:
    if not fiche.cv:
        return False
    fiche.cv.delete(save=False)
    fiche.cv_nom, fiche.cv_depose_le = "", None
    fiche.save()
    return True


def _apres(section, suivant):
    if suivant == "suggestions":
        return redirect("web-pour-vous")
    return redirect(f"{reverse('web-profil')}#{suivant if suivant in ONGLETS else section}")


def _profil_visible(requete, user_id):
    # 404 et non 403 : on ne confirme pas qu'un autre compte a deposé un fichier.
    if requete.user.pk != user_id and not est_admin(requete.user):
        raise Http404
    return get_object_or_404(Profil, user_id=user_id)


def cv(requete, user_id):
    fiche = _profil_visible(requete, user_id)
    if not fiche.cv:
        raise Http404
    nom = fiche.cv_nom or "cv" + os.path.splitext(fiche.cv.name)[1]
    return FileResponse(fiche.cv.open("rb"), as_attachment=True, filename=nom)


def photo(requete, user_id):
    fiche = _profil_visible(requete, user_id)
    if not fiche.photo:
        raise Http404
    ext = os.path.splitext(fiche.photo.name)[1].lower()
    reponse = FileResponse(fiche.photo.open("rb"), content_type=TYPES_PHOTO.get(ext))
    reponse["Cache-Control"] = "private, max-age=3600"
    return reponse


def _resume(user) -> list:
    """Les critères en clair, pour dire à l'utilisateur sur quoi portent ses suggestions."""
    fiche, prefs = Profil.de(user), Preferences.de(user)
    lieux = [p.nom for p in prefs.pays.all()] + [geo.LIBELLE.get(r, r) for r in prefs.regions]
    lieux += [v for v in prefs.villes.split(", ") if v]
    if not lieux and fiche.pays_id:
        lieux = [f"{fiche.pays.nom} (pays de résidence)"]
    types = [libelle for code, libelle in Preferences.TYPES if code in prefs.types_offres]
    return [(titre, valeurs) for titre, valeurs in (
        ("Lieux", lieux),
        ("Domaines", [s.nom for s in fiche.secteurs.all()]),
        ("Catégories", [c.nom for c in fiche.categories.all()]),
        ("Compétences", [c.nom for c in fiche.competences.all()]),
        ("Mots-clés", [m for m in fiche.mots_cles.split(", ") if m]),
        ("Types", types or ["Marchés et postes"]),
    ) if valeurs]


def pour_vous(requete):
    criteres, offres = suggestions(requete.user)
    page = Paginator(offres, PAR_PAGE).get_page(requete.GET.get("page"))
    aujourdhui, libelles = timezone.now().date(), libelles_secteurs()
    for offre in page:
        annoter(offre, aujourdhui, libelles)
    return render(requete, "offres/pour_vous.html", {
        "page": page, "vide": criteres.vide, "seuil": criteres.seuil,
        "resume": _resume(requete.user), "completion": Profil.de(requete.user).completion(),
    })


@require_POST
def guide_vu(requete):
    """Le guide d'une page a été vu ou passé : il ne démarrera plus seul."""
    page = requete.POST.get("page", "")
    if not re.fullmatch(r"[a-z0-9-]{1,50}", page):
        return HttpResponseBadRequest("Page inconnue.")
    fiche = Profil.de(requete.user)
    if page not in fiche.guides_vus:
        fiche.guides_vus = (fiche.guides_vus + [page])[-50:]
        fiche.save(update_fields=["guides_vus"])
    return HttpResponse(status=204)


def mes_notifications(requete):
    lot = Notification.objects.filter(user=requete.user).select_related("offre")
    return render(requete, "offres/notifications.html", {
        "page": Paginator(lot, 30).get_page(requete.GET.get("page")),
        "alertes_actives": Preferences.de(requete.user).notifications,
    })


def abonnement(requete):
    """Plans proposés et demandes de l'utilisateur. Pas de paiement en ligne :
    la demande attend qu'un admin la valide (page Abonnements, `abonnements_admin`)."""
    if requete.method == "POST":
        if not requete.POST.get("plan", "").isdigit():
            return HttpResponseBadRequest("Plan inconnu.")
        plan = get_object_or_404(Plan, pk=requete.POST["plan"], actif=True)
        try:
            demander_plan(requete.user, plan)
            messages.success(requete, f"Demande « {plan.nom} » envoyée. Elle sera activée à réception du paiement.")
        except ValueError as exc:
            messages.error(requete, str(exc))
        return redirect("web-abonnement")
    du_jour, lots = Consultation.du_jour(requete.user)
    return render(requete, "offres/abonnement.html", {
        "plans": Plan.objects.filter(actif=True),
        "demandes": requete.user.abonnements.select_related("plan")[:20],
        "du_jour": du_jour, "lots": lots, "gratuits": Consultation.LIMITE_JOUR,
        "aujourdhui": timezone.localdate(),
    })


def demander_plan(user, plan):
    """Crée la demande d'abonnement ; une seule en attente à la fois."""
    if user.abonnements.filter(statut=Abonnement.EN_ATTENTE).exists():
        raise ValueError("Vous avez déjà une demande en attente de validation.")
    return Abonnement.objects.create(user=user, plan=plan)


@admin_requis
def abonnements_admin(requete):
    """ADMIN : demandes à valider, historique des abonnements et plans proposés."""
    statut = requete.GET.get("statut", "")
    historique = (Abonnement.objects.exclude(statut=Abonnement.EN_ATTENTE)
                  .select_related("user", "plan", "valide_par"))
    if statut in (Abonnement.VALIDE, Abonnement.REFUSE):
        historique = historique.filter(statut=statut)
    return render(requete, "offres/abonnements_admin.html", {
        "attente": (Abonnement.objects.filter(statut=Abonnement.EN_ATTENTE)
                    .select_related("user", "plan").order_by("demande_le")),
        "page": Paginator(historique, 30).get_page(requete.GET.get("page")),
        "statut": statut,
        # Un préfixe par plan : sinon tous les formulaires de la page partagent les mêmes id.
        "plans": [(plan, PlanForm(instance=plan, prefix=f"p{plan.pk}")) for plan in Plan.objects.all()],
        "nouveau": PlanForm(prefix="nouveau", initial={"actif": True}),
        "aujourdhui": timezone.localdate(),
    })


@admin_requis
@require_POST
def decider_abonnement(requete, abonnement_id, action):
    """Valider (paiement reçu) ou refuser une demande en attente."""
    demande = get_object_or_404(Abonnement.objects.select_related("user", "plan"),
                                pk=abonnement_id, statut=Abonnement.EN_ATTENTE)
    if action == "valider":
        demande.valider(requete.user)
        messages.success(requete, f"Abonnement « {demande.plan.nom} » de {demande.user.email} validé.")
    elif action == "refuser":
        demande.refuser()
        messages.success(requete, f"Demande « {demande.plan.nom} » de {demande.user.email} refusée.")
    else:
        raise Http404
    return redirect("web-abonnements")


@admin_requis
@require_POST
def enregistrer_plan(requete, plan_id=None):
    """Crée un plan, ou modifie celui-ci. Les abonnements déjà validés gardent leurs crédits."""
    plan = get_object_or_404(Plan, pk=plan_id) if plan_id else None
    form = PlanForm(requete.POST, instance=plan, prefix=f"p{plan_id}" if plan_id else "nouveau")
    if form.is_valid():
        form.save()
        messages.success(requete, f"Plan « {form.instance.nom} » enregistré.")
    else:
        erreurs = [f"{form.fields[c].label} : {m}" if c in form.fields else m
                   for c, liste in form.errors.items() for m in liste]
        messages.error(requete, "Plan non enregistré. " + " ".join(erreurs))
    return redirect(reverse("web-abonnements") + "#plans")
