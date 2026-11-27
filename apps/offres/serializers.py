"""Serialiseurs de l'API applicative /api/v1/ : la forme exacte de chaque reponse
et de chaque corps attendu. drf-spectacular en tire le schema OpenAPI
(/api/v1/schema/), d'ou se generent les clients Next.js et Flutter.

Les regles metier n'y sont pas recopiees : le profil est valide par les
formulaires du site (forms.py), l'administration par operations.py. Ici, les
types et les bornes, rien de plus.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .comptes import est_admin
from .forms import CVForm, DomainesForm, InfosPersonnellesForm, InfosProForm, PreferencesForm
from .models import (Abonnement, CleApi, Consultation, Inscription, Parametres, Plan, Preferences,
                     Profil, Suivi)
from .operations import CRITERES_SCORE, NOTE_MAX
from .services import geo

S = serializers


def choix(liste) -> list:
    return [{"code": code, "libelle": libelle} for code, libelle in liste]


def page_de(element, nom, **extra):
    """Classe de page paginee (pour le schema) : total, page, pages, par_page, resultats."""
    champs = {"total": S.IntegerField(), "page": S.IntegerField(), "pages": S.IntegerField(),
              "par_page": S.IntegerField(), **extra, "resultats": element(many=True)}
    return type(nom, (S.Serializer,), champs)


class ChoixSerializer(S.Serializer):
    code = S.CharField()
    libelle = S.CharField()


class IdNomSerializer(S.Serializer):
    id = S.IntegerField()
    nom = S.CharField()


class MessageSerializer(S.Serializer):
    message = S.CharField()


class ErreurSerializer(S.Serializer):
    erreur = S.CharField()
    champs = S.DictField(child=S.ListField(child=S.CharField()), required=False,
                         help_text="Erreurs par champ, pour une saisie invalide.")


# ------------------------------------------------------------- reference

class ReferenceProfilSerializer(S.Serializer):
    secteurs = IdNomSerializer(many=True)
    categories = IdNomSerializer(many=True)
    pays = IdNomSerializer(many=True)
    regions = ChoixSerializer(many=True)
    types_offres = ChoixSerializer(many=True)
    niveaux_etudes = ChoixSerializer(many=True)
    types_contrat = ChoixSerializer(many=True)
    disponibilites = ChoixSerializer(many=True)
    modes_travail = ChoixSerializer(many=True)


class ReferenceSerializer(S.Serializer):
    etats = ChoixSerializer(many=True, help_text="Valeurs de ?etat= (onglets de la liste).")
    natures = ChoixSerializer(many=True)
    secteurs = ChoixSerializer(many=True, help_text="Valeurs de ?secteur=.")
    pays = ChoixSerializer(many=True, help_text="Valeurs de ?pays=.")
    regions = ChoixSerializer(many=True, help_text="Valeurs de ?region=.")
    statuts_suivi = ChoixSerializer(many=True)
    profil = ReferenceProfilSerializer(help_text="Choix du profil, designes par id.")
    essai_jours = S.IntegerField(help_text="Durée de l'essai gratuit des nouveaux comptes.")


# ------------------------------------------------------------------ compte

def credits(user) -> dict:
    if est_admin(user):
        return {"illimites": True}
    du_jour, lots = Consultation.du_jour(user)
    essai = Inscription.essai(user)
    return {"illimites": bool(essai), "essai_jusqu_au": essai, "du_jour": du_jour, "lots": lots,
            "total": du_jour + lots}


class CreditsSerializer(S.Serializer):
    illimites = S.BooleanField(help_text="Admin, ou essai gratuit en cours : aucune limite.")
    essai_jusqu_au = S.DateField(required=False, allow_null=True,
                                 help_text="Dernier jour de l'essai gratuit en cours ; absent pour un admin.")
    du_jour = S.IntegerField(required=False, help_text="Credits du jour (abonnements par jour).")
    lots = S.IntegerField(required=False, help_text="Credits de lots d'abonnement en reserve.")
    total = S.IntegerField(required=False)


class MoiSerializer(S.Serializer):
    id = S.IntegerField()
    email = S.EmailField()
    prenom = S.CharField(allow_blank=True)
    nom = S.CharField(allow_blank=True)
    admin = S.BooleanField()
    avatar = S.CharField(allow_null=True)
    completion = S.IntegerField(help_text="Profil rempli, en %.")
    credits = CreditsSerializer()


# ------------------------------------------------------------------ offres

class OffreSerializer(S.Serializer):
    """Offre annotee par views_web.annoter. Le lien officiel n'est servi qu'aux
    admins : un utilisateur l'obtient par /offres/<id>/consulter/ (un credit)."""

    id = S.CharField()
    titre = S.CharField()
    titre_lisible = S.CharField()
    organisation = S.CharField(allow_null=True)
    pays = S.CharField(allow_null=True)
    region = S.CharField()
    region_libelle = S.CharField()
    source = S.CharField()
    source_nom = S.CharField()
    nature = S.CharField(allow_null=True)
    secteur = S.CharField(allow_null=True)
    secteur_libelle = S.CharField()
    categorie = S.CharField(allow_null=True)
    pertinent = S.BooleanField()
    date_publication = S.DateField(allow_null=True)
    date_limite = S.DateField(allow_null=True)
    etat_echeance = S.ChoiceField(choices=["inconnue", "presumee", "passee", "urgente", "proche", "lointaine"])
    jours = S.IntegerField(help_text="Jours restants (negatif : passee) ; sans echeance : age de l'offre.")
    lien_etat = S.CharField(allow_null=True)
    a_un_lien = S.SerializerMethodField()
    lien = S.URLField(required=False, allow_null=True, help_text="Admins seulement.")

    def get_a_un_lien(self, offre) -> bool:
        return bool(offre.lien)

    def to_representation(self, offre):
        donnees = super().to_representation(offre)
        if not est_admin(self.context["request"].user):
            donnees.pop("lien", None)
        return donnees


class SuggestionSerializer(OffreSerializer):
    score = S.IntegerField(help_text="Correspondance avec le profil, sur 100.")


class OffreCourteSerializer(S.Serializer):
    id = S.CharField()
    titre = S.CharField()


class VoisineSerializer(OffreCourteSerializer):
    date_limite = S.DateField(allow_null=True)


class SuiviSerializer(S.Serializer):
    statut = S.ChoiceField(choices=Suivi.STATUT_CHOICES)
    statut_libelle = S.CharField(source="get_statut_display")
    note = S.CharField(allow_blank=True)
    echeance = S.DateField(allow_null=True)
    echeance_saisie_le = S.DateTimeField(allow_null=True)
    decide_par = S.SerializerMethodField()
    decide_par_cle = S.SerializerMethodField()
    maj_le = S.DateTimeField()

    def get_decide_par(self, suivi) -> str | None:
        return suivi.decide_par.email if suivi.decide_par_id else None

    def get_decide_par_cle(self, suivi) -> str | None:
        return suivi.decide_par_cle.nom if suivi.decide_par_cle_id else None


class SuiviLigneSerializer(SuiviSerializer):
    offre = OffreCourteSerializer()


class OffreDetailSerializer(OffreSerializer):
    description = S.CharField(allow_null=True)
    raison = S.CharField(allow_null=True)
    date_ajout = S.DateTimeField()
    lien_verifie_le = S.DateTimeField(allow_null=True)
    deja_consultee = S.BooleanField(help_text="Ouverte aujourd'hui : la rouvrir est gratuit.")
    voisines = VoisineSerializer(many=True)
    suivi = SuiviSerializer(source="suivi_api", allow_null=True, required=False,
                            help_text="Admins seulement.")

    def to_representation(self, offre):
        donnees = super().to_representation(offre)
        if not est_admin(self.context["request"].user):
            donnees.pop("suivi", None)
        return donnees


class ConsulterSerializer(S.Serializer):
    lien = S.URLField()
    credits = CreditsSerializer()


class CreditsEpuisesSerializer(S.Serializer):
    erreur = S.CharField()
    code = S.ChoiceField(choices=["credits_epuises"])
    credits = CreditsSerializer()


class PointCarteSerializer(S.Serializer):
    lieu = S.CharField()
    lat = S.FloatField()
    lon = S.FloatField()
    region = S.CharField()
    total = S.IntegerField()
    marches = S.IntegerField()
    emplois = S.IntegerField()
    urgentes = S.IntegerField()
    exemples = OffreCourteSerializer(many=True)


class CarteSerializer(S.Serializer):
    points = PointCarteSerializer(many=True, help_text="Chaque point porte aussi un compteur par code de secteur.")
    total = S.IntegerField()
    sans_position = S.IntegerField()


# ------------------------------------------------------------------ profil

class SectionSerializer(S.Serializer):
    """Une section du profil. Les champs typent la saisie (schema) ; la regle
    reste celle du formulaire du site, applique tel quel aux donnees recues."""

    formulaire = None

    def validate(self, attrs):
        instance = self.context.get("instance")
        form = self.formulaire(self.initial_data, self.context.get("fichiers") or None,
                               **({"instance": instance} if instance is not None else {}))
        if not form.is_valid():
            raise S.ValidationError({nom: [str(m) for m in liste] for nom, liste in form.errors.items()})
        self.form = form
        return attrs

    def save(self, **kwargs):
        return self.form.save()


class PersoSerializer(SectionSerializer):
    formulaire = InfosPersonnellesForm
    first_name = S.CharField(max_length=150, allow_blank=True, required=False)
    last_name = S.CharField(max_length=150, allow_blank=True, required=False)
    telephone = S.CharField(allow_blank=True, required=False)
    adresse = S.CharField(allow_blank=True, required=False)
    ville = S.CharField(allow_blank=True, required=False)
    region = S.CharField(allow_blank=True, required=False)
    code_postal = S.CharField(allow_blank=True, required=False)
    pays = S.IntegerField(allow_null=True, required=False, help_text="id d'un pays de /reference/ (profil.pays).")
    date_naissance = S.DateField(allow_null=True, required=False)
    photo = S.FileField(write_only=True, required=False, help_text="Multipart : PNG, JPEG ou WebP, 2 Mo.")
    supprimer_photo = S.BooleanField(write_only=True, required=False)


class ProSerializer(SectionSerializer):
    formulaire = InfosProForm
    titre = S.CharField(allow_blank=True, required=False)
    description = S.CharField(allow_blank=True, required=False)
    annees_experience = S.IntegerField(allow_null=True, required=False, min_value=0)
    niveau_etudes = S.ChoiceField(choices=Profil.NIVEAUX, allow_blank=True, required=False)
    type_contrat = S.ChoiceField(choices=Profil.CONTRATS, allow_blank=True, required=False)
    disponibilite = S.ChoiceField(choices=Profil.DISPONIBILITES, allow_blank=True, required=False)
    mode_travail = S.ChoiceField(choices=Profil.MODES, allow_blank=True, required=False)


class DomainesSerializer(SectionSerializer):
    formulaire = DomainesForm
    secteurs = S.ListField(child=S.IntegerField(), required=False, help_text="ids de /reference/ (profil.secteurs).")
    categories = S.ListField(child=S.IntegerField(), required=False)
    competences_texte = S.CharField(allow_blank=True, required=False, help_text="Séparées par des virgules, 30 au plus.")
    mots_cles = S.CharField(allow_blank=True, required=False)


class PreferencesSerializer(SectionSerializer):
    formulaire = PreferencesForm
    pays = S.ListField(child=S.IntegerField(), required=False)
    regions = S.ListField(child=S.ChoiceField(choices=[c for c in geo.LIBELLES if c[0] != geo.INCONNUE]),
                          required=False)
    villes = S.CharField(allow_blank=True, required=False)
    types_offres = S.ListField(child=S.ChoiceField(choices=Preferences.TYPES), required=False)
    teletravail = S.BooleanField(required=False)
    seuil = S.IntegerField(min_value=0, max_value=100, required=False, help_text="Score minimal des suggestions.")
    notifications = S.BooleanField(required=False)


class CvSerializer(S.Serializer):
    nom = S.CharField()
    depose_le = S.DateTimeField()


class CvDepotSerializer(SectionSerializer):
    formulaire = CVForm
    fichier = S.FileField(help_text="PDF ou DOCX, 5 Mo au plus.")


class ResumeSerializer(S.Serializer):
    titre = S.CharField()
    valeurs = S.ListField(child=S.CharField())


class ProfilSerializer(S.Serializer):
    """Chaque section a les noms de champs de sa saisie : ce que renvoie GET /profil/,
    on le renvoie modifie a PUT /profil/<section>/."""

    perso = PersoSerializer()
    pro = ProSerializer()
    domaines = DomainesSerializer()
    preferences = PreferencesSerializer()
    photo = S.CharField(allow_null=True)
    cv = CvSerializer(allow_null=True)
    completion = S.IntegerField()
    resume = ResumeSerializer(many=True)


# ------------------------------------------------------------- abonnements

class PlanSerializer(S.ModelSerializer):
    prix_credit = S.DecimalField(max_digits=12, decimal_places=4, coerce_to_string=False, read_only=True,
                                 help_text="Prix d'un credit en euros, pour comparer les plans.")

    class Meta:
        model = Plan
        fields = ["id", "nom", "prix", "credits", "par_jour", "duree_jours", "actif", "prix_credit"]
        extra_kwargs = {"credits": {"min_value": 1}, "prix": {"coerce_to_string": False}}


class PlanCourtSerializer(S.Serializer):
    id = S.IntegerField()
    nom = S.CharField()
    prix = S.DecimalField(max_digits=8, decimal_places=2, coerce_to_string=False, help_text="En euros.")


class AbonnementSerializer(S.Serializer):
    id = S.IntegerField()
    plan = PlanCourtSerializer()
    statut = S.ChoiceField(choices=Abonnement.STATUTS)
    statut_libelle = S.CharField(source="get_statut_display")
    etat = S.SerializerMethodField()
    demande_le = S.DateTimeField()
    debut = S.DateField(allow_null=True)
    fin = S.DateField(allow_null=True, help_text="Dernier jour inclus ; null : sans fin.")
    credits_jour = S.IntegerField()
    credits_restants = S.IntegerField()

    def get_etat(self, demande) -> str:
        """attente, refuse, actif ou termine."""
        from django.utils import timezone
        if demande.statut != Abonnement.VALIDE:
            return demande.statut
        return "termine" if demande.fin and demande.fin < timezone.localdate() else "actif"


class UtilisateurCourtSerializer(S.Serializer):
    id = S.IntegerField()
    email = S.EmailField()


class AbonnementAdminSerializer(AbonnementSerializer):
    utilisateur = UtilisateurCourtSerializer(source="user")
    valide_par = S.SerializerMethodField()

    def get_valide_par(self, demande) -> str | None:
        return demande.valide_par.email if demande.valide_par_id else None


class MesAbonnementsSerializer(S.Serializer):
    credits = CreditsSerializer()
    abonnements = AbonnementSerializer(many=True)


class DemandeSerializer(S.Serializer):
    plan = S.PrimaryKeyRelatedField(queryset=Plan.objects.filter(actif=True), help_text="id d'un plan proposé.")


class DemandeCreeeSerializer(S.Serializer):
    message = S.CharField()
    abonnement = AbonnementSerializer()


class NotificationSerializer(S.Serializer):
    id = S.IntegerField()
    offre = OffreCourteSerializer()
    score = S.IntegerField()
    statut = S.CharField()
    statut_libelle = S.CharField(source="get_statut_display")
    date = S.SerializerMethodField()

    def get_date(self, notification) -> str:
        return (notification.envoye_le or notification.cree_le).isoformat()


# ------------------------------------------------------------------ admin

class DecisionSerializer(S.Serializer):
    statut = S.ChoiceField(choices=Suivi.STATUT_CHOICES)
    note = S.CharField(required=False, allow_blank=True, allow_null=True, max_length=NOTE_MAX,
                       help_text="Absente : inchangée ; vide : effacée.")


class EcheanceSerializer(S.Serializer):
    echeance = S.DateField()


class VerdictSerializer(S.Serializer):
    pertinent = S.BooleanField()


class StatistiquesSerializer(S.Serializer):
    total = S.IntegerField()
    retenues = S.IntegerField()
    ouvertes = S.IntegerField()
    actionnables = S.IntegerField()
    par_nature = S.DictField(child=S.IntegerField())
    par_secteur = S.DictField(child=S.IntegerField())
    par_source = S.DictField(child=S.IntegerField())
    par_categorie = S.DictField(child=S.IntegerField())
    par_region = S.DictField(child=S.IntegerField())
    suivi = S.DictField(child=S.IntegerField())


class SourceSerializer(S.Serializer):
    source = S.CharField()
    total = S.IntegerField()
    retenues = S.IntegerField()
    actionnables = S.IntegerField()
    derniere_collecte = S.DateTimeField()


class PhaseSerializer(S.Serializer):
    libelle = S.CharField()
    etat = S.ChoiceField(choices=["faite", "active", "a_venir"])


class TacheSerializer(S.Serializer):
    id = S.IntegerField()
    nom = S.CharField()
    libelle = S.CharField()
    statut = S.CharField()
    statut_libelle = S.CharField(source="get_statut_display")
    automatique = S.BooleanField()
    phase = S.IntegerField()
    phases = S.SerializerMethodField()
    etape = S.CharField(allow_blank=True)
    courant = S.IntegerField()
    total = S.IntegerField()
    pourcentage = S.IntegerField()
    detail = S.CharField(allow_blank=True)
    debut = S.DateTimeField()
    fin = S.DateTimeField(allow_null=True)
    duree_secondes = S.SerializerMethodField()

    @extend_schema_field(PhaseSerializer(many=True))
    def get_phases(self, tache):
        return [{"libelle": l, "etat": e} for l, e in tache.phases]

    def get_duree_secondes(self, tache) -> int:
        return int(tache.duree.total_seconds())


class TacheDetailSerializer(TacheSerializer):
    journal = S.SerializerMethodField()

    def get_journal(self, tache) -> str:
        return tache.journal()


class TypeTacheSerializer(S.Serializer):
    nom = S.CharField()
    libelle = S.CharField()
    phases = S.ListField(child=S.CharField())


class TachesSerializer(S.Serializer):
    active = TacheSerializer(allow_null=True)
    a_reprendre = TacheSerializer(many=True)
    automatismes_suspendus = S.BooleanField()
    intervalle_collecte = S.IntegerField()
    types = TypeTacheSerializer(many=True)
    nb_sources = S.IntegerField()
    historique = TacheSerializer(many=True)


class TacheReponseSerializer(S.Serializer):
    message = S.CharField()
    tache = TacheSerializer()


class CollecteSerializer(S.Serializer):
    intervalle_collecte = S.IntegerField(min_value=1, max_value=24)
    heure_nuit = S.RegexField(r"^\d{2}:\d{2}$", required=False, allow_blank=True, help_text="HH:MM")
    pause_weekend = S.BooleanField(required=False, help_text="Absent : inchangé.")


class EmailSerializer(S.Serializer):
    smtp_hote = S.CharField(max_length=255, allow_blank=True, required=False, help_text="Vide : serveur du .env.")
    smtp_port = S.IntegerField(min_value=1, max_value=65535, allow_null=True, required=False)
    smtp_securite = S.ChoiceField(choices=Parametres.SECURITES_SMTP, required=False)
    smtp_utilisateur = S.CharField(allow_blank=True, required=False)
    smtp_mot_de_passe = S.CharField(write_only=True, allow_blank=True, required=False,
                                    help_text="Vide : inchangé.")
    destinataires = S.ListField(child=S.CharField(), required=False)


class EmailEnregistreSerializer(MessageSerializer):
    mot_de_passe_efface = S.BooleanField()


class EmailTestSerializer(MessageSerializer):
    niveau = S.ChoiceField(choices=["succes", "info"])


PoidsSerializer = type("PoidsSerializer", (S.Serializer,), {
    code: S.IntegerField(min_value=0, max_value=100, help_text=libelle) for code, libelle in CRITERES_SCORE})


class PertinenceSerializer(S.Serializer):
    code = S.CharField()
    libelle = S.CharField()
    poids = S.IntegerField()


class SourceParametreSerializer(S.Serializer):
    source = S.CharField()
    nom = S.CharField()
    site = S.CharField()
    domaine = S.CharField()
    total = S.IntegerField()
    derniere = S.DateTimeField(allow_null=True)


class ParametresCollecteSerializer(S.Serializer):
    intervalle_collecte = S.IntegerField()
    heure_nuit = S.CharField()
    prochaine = S.DateTimeField()
    automatismes_suspendus = S.BooleanField()
    pause_weekend = S.BooleanField()
    derniere_auto = TacheSerializer(allow_null=True)
    derniere_nuit = TacheSerializer(allow_null=True)


class ParametresEmailSerializer(S.Serializer):
    source = S.ChoiceField(choices=["ecran", "env", "console"])
    smtp_hote = S.CharField(allow_blank=True)
    smtp_port = S.IntegerField()
    smtp_securite = S.CharField()
    smtp_utilisateur = S.CharField(allow_blank=True)
    mot_de_passe_enregistre = S.BooleanField()
    destinataires = S.ListField(child=S.CharField())
    securites = ChoixSerializer(many=True)


class ParametresSerializer(S.Serializer):
    collecte = ParametresCollecteSerializer()
    email = ParametresEmailSerializer()
    pertinence = PertinenceSerializer(many=True)
    sources = SourceParametreSerializer(many=True)


class NomSerializer(S.Serializer):
    nom = S.CharField(max_length=100)


class CatalogueSerializer(S.Serializer):
    id = S.IntegerField()
    code = S.CharField()
    nom = S.CharField()
    actif = S.BooleanField()
    nombre_offres = S.IntegerField()


class CleSerializer(S.ModelSerializer):
    active = S.BooleanField(read_only=True)

    class Meta:
        model = CleApi
        fields = ["id", "nom", "active", "cree_le", "derniere_utilisation", "revoque_le"]


class CleCreeeSerializer(MessageSerializer):
    jeton = S.CharField(help_text="Montré une seule fois : seule son empreinte est gardée.")
