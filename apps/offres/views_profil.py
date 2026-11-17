"""Pages du compte : profil (sections A à E), CV, suggestions, notifications.

Chaque section du profil s'enregistre à part : une erreur dans l'une ne fait
pas perdre la saisie des autres. Les fichiers (CV, photo) ne sortent que par
`cv` et `photo`, qui vérifient que le demandeur est le propriétaire ou un admin.
"""

import os

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .comptes import est_admin
from .fichiers import TYPES_PHOTO
from .forms import CVForm, DomainesForm, InfosPersonnellesForm, InfosProForm, PreferencesForm
from .models import Notification, Preferences, Profil
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
                fichier = form_cv.cleaned_data["fichier"]
                if fiche.cv:
                    fiche.cv.delete(save=False)
                fiche.cv = fichier
                fiche.cv_nom = os.path.basename(fichier.name)[:255]
                fiche.cv_depose_le = timezone.now()
                fiche.save()
                messages.success(requete, "CV enregistré.")
                return _apres("cv", suivant)
            onglet = "cv"
        elif section == "cv-supprimer":
            if fiche.cv:
                fiche.cv.delete(save=False)
                fiche.cv_nom, fiche.cv_depose_le = "", None
                fiche.save()
                messages.success(requete, "CV supprimé.")
            return _apres("cv", "")
        else:
            return HttpResponseBadRequest("Section inconnue.")

    return render(requete, "offres/profil.html", {
        "fiche": fiche, "formulaires": formulaires, "form_cv": form_cv,
        "onglet": onglet, "avatar": _avatar(user, fiche), "completion": fiche.completion(),
        "bienvenue": "bienvenue" in requete.GET,
    }, status=400 if onglet else 200)


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


def mes_notifications(requete):
    lot = Notification.objects.filter(user=requete.user).select_related("offre")
    return render(requete, "offres/notifications.html", {
        "page": Paginator(lot, 30).get_page(requete.GET.get("page")),
        "alertes_actives": Preferences.de(requete.user).notifications,
    })
