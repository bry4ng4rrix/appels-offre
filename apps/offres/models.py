from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

#: Au-dela de ce nombre de jours depuis sa publication, une offre SANS date
#: limite est presumee close. 67 % des offres retenues n'ont aucune echeance
#: (toute la BAD : elle ne vit que dans le PDF du dossier) ; les tenir pour
#: ouvertes indefiniment gonflait le compteur d'opportunites. 30 jours parce
#: que les fenetres de depot BAD / Banque mondiale vont de 14 a 21 jours.
#: Le repere est date_publication, avec repli sur date_ajout.
PRESUMEE_CLOSE_JOURS = 30


def ouvertes(lot):
    """Encore ouvertes et non retirees par leur source. Sans echeance, une
    offre est presumee close passe PRESUMEE_CLOSE_JOURS (meme regle partout :
    ecran, API, commandes -- sinon chacun verrait des offres differentes)."""
    limite = timezone.now() - timedelta(days=PRESUMEE_CLOSE_JOURS)
    return lot.exclude(lien_etat__in=Offre.LIEN_FERME).filter(
        Q(date_limite__gte=timezone.now().date())
        | Q(date_limite__isnull=True, date_publication__gte=limite.date())
        | Q(date_limite__isnull=True, date_publication__isnull=True,
            date_ajout__gte=limite))


def actionnables(lot):
    """Retenues, encore ouvertes, non retirees."""
    return ouvertes(lot.filter(pertinent=True))


class Offre(models.Model):
    NATURE_CHOICES = [
        ("marche", "Marché"),
        ("emploi", "Emploi"),
    ]
    SECTEUR_CHOICES = [
        ("informatique", "Informatique"),
        ("construction", "Construction"),
        ("agriculture", "Agriculture"),
        ("eau", "Eau"),
        ("environnement", "Environnement"),
        ("autre", "Autre"),
    ]
    LIEN_ETAT_CHOICES = [
        ("ouverte", "En ligne"),
        ("introuvable", "Retirée (404)"),
        ("close", "Annoncée close"),
        ("illisible", "Illisible"),
    ]
    #: Les deux etats qui retirent une offre des actionnables. "illisible"
    #: n'en fait PAS partie : un 403 ou une panne du site ne prouvent rien.
    LIEN_FERME = ("introuvable", "close")

    id = models.CharField(max_length=255, primary_key=True)
    source = models.CharField(max_length=100, db_index=True)
    titre = models.TextField()
    organisation = models.TextField(null=True, blank=True)
    pays = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    date_publication = models.DateField("publiée le", null=True, blank=True, db_index=True)
    date_limite = models.DateField("date limite", null=True, blank=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    lien = models.URLField(max_length=2000, null=True, blank=True)

    # Qualification par le moteur de regles
    pertinent = models.BooleanField("retenue", default=False, db_index=True)
    nature = models.CharField(max_length=20, choices=NATURE_CHOICES, null=True, blank=True)
    secteur = models.CharField(max_length=30, choices=SECTEUR_CHOICES, null=True, blank=True,
                               db_index=True)
    categorie = models.CharField("catégorie", max_length=255, null=True, blank=True)
    raison = models.TextField(null=True, blank=True)

    # Renseignes par verifier_liens, jamais par le tri : une offre retiree
    # par sa source ne redevient pas ouverte au prochain re-tri.
    lien_verifie_le = models.DateTimeField("lien vérifié le", null=True, blank=True)
    lien_etat = models.CharField("état du lien", max_length=20, choices=LIEN_ETAT_CHOICES,
                                 null=True, blank=True, db_index=True)

    date_ajout = models.DateTimeField("ajoutée le", auto_now_add=True, db_index=True)
    date_maj = models.DateTimeField("mise à jour le", auto_now=True)

    class Meta:
        db_table = "offres"
        ordering = ["-date_ajout"]
        verbose_name = "Offre"
        verbose_name_plural = "Offres"

    def __str__(self):
        return f"[{self.source}] {self.titre[:70]}"

    @property
    def jours_restants(self):
        if not self.date_limite:
            return None
        return (self.date_limite - timezone.now().date()).days

    @property
    def est_ouverte(self) -> bool:
        if self.lien_etat in self.LIEN_FERME:
            return False
        if self.date_limite:
            return self.date_limite >= timezone.now().date()
        date_ref = self.date_publication or self.date_ajout.date()
        return (timezone.now().date() - date_ref).days <= PRESUMEE_CLOSE_JOURS

    @property
    def progression_temps(self) -> int:
        """% de temps ecoule entre publication et echeance (barre de progression)."""
        if not self.date_limite:
            return 50
        # Repli sur la date de collecte : UNjobnet ne publie pas la date de parution.
        debut = self.date_publication or (self.date_ajout and self.date_ajout.date())
        if not debut:
            return 50
        total = (self.date_limite - debut).days
        if total <= 0:
            return 100
        ecoule = (timezone.now().date() - debut).days
        return max(0, min(100, int((ecoule / total) * 100)))


class CleApi(models.Model):
    """Jeton d'acces aux endpoints /api/. Seule l'empreinte SHA-256 est stockee :
    le jeton fait 256 bits d'alea, un hachage lent n'apporterait rien."""

    PREFIXE = "veille_"
    nom = models.CharField(max_length=80, unique=True)
    empreinte = models.CharField(max_length=64, unique=True, db_index=True, editable=False)
    cree_le = models.DateTimeField(auto_now_add=True)
    derniere_utilisation = models.DateTimeField(null=True, blank=True, editable=False)
    revoque_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "cles_api"
        ordering = ["-cree_le"]
        verbose_name = "clé d'API"
        verbose_name_plural = "clés d'API"

    def __str__(self):
        return f"{self.nom} ({'active' if self.active else 'révoquée'})"

    @property
    def active(self) -> bool:
        return self.revoque_le is None


class Suivi(models.Model):
    """Decision commerciale humaine sur une offre. Table separee d'Offre pour
    qu'un re-tri n'ecrase jamais une decision."""

    A_ETUDIER = "a_etudier"
    CANDIDATURE = "candidature"
    GAGNE = "gagne"
    PERDU = "perdu"
    HORS_SUJET = "hors_sujet"
    STATUT_CHOICES = [
        (A_ETUDIER, "À étudier"),
        (CANDIDATURE, "Candidature déposée"),
        (GAGNE, "Gagné"),
        (PERDU, "Perdu"),
        (HORS_SUJET, "Hors sujet"),
    ]
    #: Les etapes reellement franchies, dans l'ordre. HORS_SUJET est une sortie.
    ENTONNOIR = [A_ETUDIER, CANDIDATURE, GAGNE]

    offre = models.OneToOneField(Offre, on_delete=models.CASCADE, related_name="suivi")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=A_ETUDIER,
                              db_index=True)
    note = models.TextField(blank=True)
    # Echeance lue a la main dans le dossier quand la source ne la publie pas.
    # offres.date_limite en recoit une copie pour que toutes les vues la lisent.
    echeance = models.DateField("échéance saisie", null=True, blank=True)
    echeance_saisie_le = models.DateTimeField(null=True, blank=True)
    decide_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, verbose_name="décidé par")
    decide_par_cle = models.ForeignKey(CleApi, null=True, blank=True,
                                       on_delete=models.SET_NULL,
                                       verbose_name="décidé par la clé")
    cree_le = models.DateTimeField(auto_now_add=True)
    maj_le = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suivi"
        ordering = ["-maj_le"]

    def __str__(self):
        return f"{self.get_statut_display()} — {self.offre_id}"
