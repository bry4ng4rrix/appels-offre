"""Formulaires du profil : une classe par section, chacune enregistrée à part."""

import re

from django import forms

from .fichiers import verifier_cv, verifier_photo
from .models import Categorie, Competence, Pays, Preferences, Profil, Secteur
from .services import geo


def liste(texte: str) -> list:
    """« Python, Django ; React » -> ["Python", "Django", "React"], sans doublon."""
    vus, sortie = set(), []
    for mot in re.split(r"[,;\n]+", texte or ""):
        mot = " ".join(mot.split())
        if mot and mot.casefold() not in vus:
            vus.add(mot.casefold())
            sortie.append(mot)
    return sortie


class Habille:
    """Donne la classe .champ aux widgets de saisie (pas aux cases a cocher)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            if not isinstance(champ.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple,
                                             forms.FileInput)):
                champ.widget.attrs.setdefault("class", "champ")


class InfosPersonnellesForm(Habille, forms.ModelForm):
    first_name = forms.CharField(label="Prénom", max_length=150, required=False)
    last_name = forms.CharField(label="Nom", max_length=150, required=False)
    photo = forms.FileField(label="Photo de profil", required=False, widget=forms.FileInput(
        attrs={"accept": "image/png,image/jpeg,image/webp"}), validators=[verifier_photo],
        help_text="PNG, JPEG ou WebP, 2 Mo au maximum.")
    supprimer_photo = forms.BooleanField(label="Retirer la photo actuelle", required=False)

    class Meta:
        model = Profil
        fields = ["telephone", "adresse", "ville", "region", "code_postal", "pays",
                  "date_naissance"]
        widgets = {"date_naissance": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
                   "telephone": forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["pays"].queryset = Pays.objects.filter(actif=True)
        self.fields["pays"].empty_label = "Choisir un pays"
        self.order_fields(["first_name", "last_name"])

    def save(self, commit=True):
        profil = super().save(commit=False)
        user = profil.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if self.cleaned_data.get("photo"):
            if profil.photo:
                profil.photo.delete(save=False)
            profil.photo = self.cleaned_data["photo"]
        elif self.cleaned_data.get("supprimer_photo") and profil.photo:
            profil.photo.delete(save=False)
        user.save(update_fields=["first_name", "last_name"])
        profil.save()
        return profil


class InfosProForm(Habille, forms.ModelForm):
    class Meta:
        model = Profil
        fields = ["titre", "description", "annees_experience", "niveau_etudes",
                  "type_contrat", "disponibilite", "mode_travail"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class DomainesForm(Habille, forms.ModelForm):
    competences_texte = forms.CharField(
        label="Compétences", required=False, max_length=1000,
        help_text="Séparées par des virgules. Ex. Python, Django, gestion de projet.")

    class Meta:
        model = Profil
        fields = ["secteurs", "categories", "mots_cles"]
        widgets = {"secteurs": forms.CheckboxSelectMultiple,
                   "categories": forms.CheckboxSelectMultiple}
        help_texts = {"mots_cles": "Séparés par des virgules. Ex. ONG, Banque mondiale, SIG."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["secteurs"].queryset = Secteur.objects.filter(actif=True)
        self.fields["categories"].queryset = Categorie.objects.filter(actif=True)
        if self.instance.pk:
            self.fields["competences_texte"].initial = ", ".join(
                c.nom for c in self.instance.competences.all())
        self.order_fields(["secteurs", "categories", "competences_texte", "mots_cles"])

    def clean_competences_texte(self):
        noms = liste(self.cleaned_data["competences_texte"])
        if len(noms) > 30:
            raise forms.ValidationError("30 compétences au maximum.")
        if any(len(n) > 80 for n in noms):
            raise forms.ValidationError("Une compétence fait au plus 80 caractères.")
        return noms

    def clean_mots_cles(self):
        return ", ".join(liste(self.cleaned_data["mots_cles"]))

    def save(self, commit=True):
        profil = super().save()
        competences = []
        for nom in self.cleaned_data["competences_texte"]:
            # Une seule ligne par nom, casse comprise (contrainte en base).
            existante = Competence.objects.filter(nom__iexact=nom).first()
            competences.append(existante or Competence.objects.create(nom=nom))
        profil.competences.set(competences)
        return profil


class PreferencesForm(Habille, forms.ModelForm):
    regions = forms.MultipleChoiceField(
        label="Régions recherchées", required=False, widget=forms.CheckboxSelectMultiple,
        choices=[(c, l) for c, l in geo.LIBELLES if c != geo.INCONNUE])
    types_offres = forms.MultipleChoiceField(
        label="Types d'offres", required=False, widget=forms.CheckboxSelectMultiple,
        choices=Preferences.TYPES, help_text="Aucun coché : marchés et postes.")

    class Meta:
        model = Preferences
        fields = ["pays", "regions", "villes", "types_offres", "teletravail", "seuil",
                  "notifications"]
        widgets = {"pays": forms.CheckboxSelectMultiple,
                   "seuil": forms.NumberInput(attrs={"min": 0, "max": 100, "step": 5})}
        labels = {"villes": "Villes recherchées"}
        help_texts = {
            "villes": "Séparées par des virgules.",
            "seuil": "Score minimal (sur 100) d'une offre pour vous être suggérée ou envoyée.",
            "notifications": "Un email après chaque passage de la collecte (toutes les 6 h) "
                             "s'il y a de nouvelles offres pour vous."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pays"].queryset = Pays.objects.filter(actif=True)

    def clean_villes(self):
        return ", ".join(liste(self.cleaned_data["villes"]))


class CVForm(forms.Form):
    fichier = forms.FileField(label="CV", validators=[verifier_cv], widget=forms.FileInput(
        attrs={"accept": ".pdf,.docx,application/pdf,"
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}),
        help_text="PDF ou DOCX, 5 Mo au maximum.")
