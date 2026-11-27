import os
import re
from datetime import time, timedelta
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db.models import Q
from django.db.models.functions import Lower
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
    # Valeur libre : les secteurs evoluent avec les offres et ne doivent pas
    # etre bloques par une liste de choix Django.
    secteur = models.CharField(max_length=100, null=True, blank=True,
                               db_index=True)
    categorie = models.CharField("catégorie", max_length=255, null=True, blank=True)
    raison = models.TextField(null=True, blank=True)

    # Renseignes par verifier_liens, jamais par le tri : une offre retiree
    # par sa source ne redevient pas ouverte au prochain re-tri.
    lien_verifie_le = models.DateTimeField("lien vérifié le", null=True, blank=True)
    lien_etat = models.CharField("état du lien", max_length=20, choices=LIEN_ETAT_CHOICES,
                                 null=True, blank=True, db_index=True)

    date_ajout = models.DateTimeField("ajoutée le", auto_now_add=True, db_index=True)
    #: Marque du tri : posee a la collecte et a chaque passage du classifieur.
    #: Le traitement automatique ne trie que les offres sans marque.
    trie_le = models.DateTimeField("triée le", null=True, blank=True, db_index=True)
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
        if not self.date_publication:
            # Sans date de parution, la jauge se remplit sur les 30 derniers jours :
            # la date de collecte donnerait 0 % a une offre a J-3.
            restants = self.jours_restants
            return max(0, min(100, int((PRESUMEE_CLOSE_JOURS - restants) * 100 / PRESUMEE_CLOSE_JOURS)))
        total = (self.date_limite - self.date_publication).days
        if total <= 0:
            return 100
        ecoule = (timezone.now().date() - self.date_publication).days
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


class Tache(models.Model):
    """Tache de fond lancee depuis l'interface (collecte, tri, liens).

    Le processus ecrit son avancement ici ; l'interface le relit chaque seconde
    pour dessiner la barre de progression. Sert aussi de verrou : une seule
    tache a la fois.

    Une tache coupee (conteneur ou VPS redemarre) passe "interrompue" ; le
    planificateur la relance, et `reprise` lui dit ce qui est deja fait
    (sources collectees, phase atteinte) pour qu'elle ne reparte pas de zero.
    """

    EN_COURS, TERMINEE, ECHEC = "en_cours", "terminee", "echec"
    #: Coupee par un redemarrage : le planificateur la reprend tout seul.
    INTERROMPUE = "interrompue"
    #: Mise en pause a la main : garde ses points de reprise, attend "Reprendre".
    SUSPENDUE = "suspendue"
    ANNULEE = "annulee"
    STATUT_CHOICES = [(EN_COURS, "En cours"), (TERMINEE, "Terminée"), (ECHEC, "Échec"),
                      (INTERROMPUE, "Interrompue"), (SUSPENDUE, "Suspendue"),
                      (ANNULEE, "Annulée")]
    #: Une tache dans l'un de ces etats peut etre reprise ou annulee.
    EN_ATTENTE = (INTERROMPUE, SUSPENDUE)
    #: nom -> (commande manage.py, libelle, phases dans l'ordre)
    TYPES = {
        "tout": ("tout", "Traitement complet", ["Collecte", "Tri", "Liens"]),
        "veille": ("veille", "Collecte", ["Collecte"]),
        "trier": ("trier", "Tri", ["Tri"]),
        "liens": ("verifier_liens", "Vérification des liens", ["Liens"]),
        "nuit": ("organiser", "Organisation de nuit", ["Catalogues", "Classement"]),
    }
    #: Une tache en cours signale sa presence toutes les 30 s (services.taches) :
    #: sans nouvelle pendant ce delai, elle est tenue pour morte. Sert quand le
    #: processus tourne dans un autre conteneur, ou son pid n'est pas verifiable.
    SILENCE_MAX = timedelta(minutes=2)
    #: Au-dela, une tache qui retombe a chaque reprise est abandonnee.
    REPRISES_MAX = 5

    nom = models.CharField(max_length=20, choices=[(k, v[1]) for k, v in TYPES.items()])
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=EN_COURS, db_index=True)
    phase = models.PositiveSmallIntegerField(default=1)
    etape = models.CharField(max_length=200, blank=True)
    courant = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    detail = models.TextField(blank=True)
    hote = models.CharField(max_length=255, blank=True)
    #: Lancee par le planificateur quotidien, et non par un bouton.
    automatique = models.BooleanField(default=False)
    pid = models.IntegerField(null=True, blank=True)
    #: Instant de demarrage du processus (/proc) : un pid reattribue apres un
    #: redemarrage de conteneur n'est pas pris pour la tache.
    pid_debut = models.BigIntegerField(null=True, blank=True)
    #: Ce qui est deja fait, pour reprendre sans repartir de zero :
    #: {"sources": [cles des sources collectees], "tri": nb de verdicts modifies}.
    reprise = models.JSONField(default=dict, blank=True)
    reprises = models.PositiveSmallIntegerField(default=0)
    debut = models.DateTimeField(auto_now_add=True)
    maj_le = models.DateTimeField(auto_now=True)
    fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "taches"
        ordering = ["-debut"]
        constraints = [
            # Le verrou "une tache a la fois", tenu par la base : deux demandes
            # simultanees ne peuvent pas lancer deux processus.
            models.UniqueConstraint(fields=["statut"], condition=Q(statut="en_cours"),
                                    name="une_seule_tache_en_cours"),
        ]

    def __str__(self):
        return f"{self.libelle} ({self.get_statut_display()})"

    @property
    def libelle(self) -> str:
        return self.TYPES[self.nom][1]

    @property
    def chemin_journal(self):
        return settings.BASE_DIR / "logs" / f"tache-{self.pk}.log"

    def journal(self, octets: int = 200_000) -> str:
        """Fin du journal de la commande (sortie standard), lue sur le disque."""
        try:
            with open(self.chemin_journal, "rb") as f:
                f.seek(0, 2)
                taille = f.tell()
                f.seek(max(0, taille - octets))
                texte = f.read().decode("utf-8", errors="replace")
        except OSError:
            return ""
        return texte if taille <= octets else "…\n" + texte.split("\n", 1)[-1]

    @property
    def journal_recent(self) -> str:
        """Les dernieres lignes, pour le panneau de progression."""
        return "\n".join(self.journal(4000).splitlines()[-8:])

    @property
    def duree(self):
        return (self.fin or timezone.now()) - self.debut

    @property
    def pourcentage(self) -> int:
        return min(100, int(self.courant * 100 / self.total)) if self.total else 0

    @property
    def phases(self) -> list:
        """[(libelle, "faite" | "active" | "a_venir")] pour les pastilles d'etapes."""
        noms = self.TYPES[self.nom][2]
        return [(n, "faite" if i + 1 < self.phase or self.statut == self.TERMINEE
                 else "active" if i + 1 == self.phase else "a_venir")
                for i, n in enumerate(noms)]

    def est_vivante(self) -> bool:
        if self.statut != self.EN_COURS:
            return False
        import socket
        if self.pid and self.hote == socket.gethostname():
            return _processus_vivant(self.pid, self.pid_debut)
        return timezone.now() - self.maj_le < self.SILENCE_MAX

    @classmethod
    def active(cls):
        """La tache en cours, ou None. Une tache dont le processus est mort
        (conteneur ou machine redemarres) passe "interrompue", a reprendre."""
        for tache in cls.objects.filter(statut=cls.EN_COURS):
            if tache.est_vivante():
                return tache
            cls.objects.filter(pk=tache.pk, statut=cls.EN_COURS).update(
                statut=cls.INTERROMPUE,
                detail=f"Interrompue pendant « {tache.etape} » : reprise automatique en attente.")
        return None

    @classmethod
    def a_reprendre(cls):
        """La plus ancienne tache interrompue, ou None."""
        return cls.objects.filter(statut=cls.INTERROMPUE).order_by("debut").first()

    @classmethod
    def arreter(cls, lot, statut: str, detail: str) -> int:
        """Suspend ou annule. Le processus d'une tache en cours le constate a son
        prochain battement (5 s au plus) et s'arrete de lui-meme, y compris s'il
        tourne dans un autre conteneur."""
        return lot.filter(statut__in=(cls.EN_COURS, *cls.EN_ATTENTE)).update(
            statut=statut, fin=timezone.now(), detail=detail)


def _stat_processus(pid: int):
    """(etat, instant de demarrage) lus dans /proc, ou None hors Linux."""
    try:
        champs = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()
        return champs[0], int(champs[19])
    except (OSError, IndexError, ValueError):
        return None


def debut_processus(pid: int):
    stat = _stat_processus(pid)
    return stat[1] if stat else None


def _processus_vivant(pid: int, debut=None) -> bool:
    import os
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    stat = _stat_processus(pid)
    if stat is None:
        return True
    etat, demarre = stat
    # Un zombie (termine, pas encore recolte) ou un pid reattribue n'est pas la tache.
    return etat != "Z" and (debut is None or demarre == debut)


def heure_par_defaut():
    """VEILLE_HEURE de l'environnement : valeur initiale, avant tout reglage a l'ecran."""
    from datetime import datetime, time
    try:
        return datetime.strptime(settings.VEILLE_HEURE, "%H:%M").time()
    except ValueError:
        return time(6, 0)


class Parametres(models.Model):
    """Reglages modifiables dans l'onglet Parametres. Une seule ligne (pk=1)."""

    heure_collecte = models.TimeField("heure de la collecte automatique", default=heure_par_defaut)
    intervalle_collecte = models.PositiveSmallIntegerField(
        "intervalle de collecte en heures", default=6)
    #: Mis a jour chaque minute par `manage.py planifier` : dit a l'ecran si un
    #: planificateur tourne pour appliquer l'heure reglee.
    planificateur_vu_le = models.DateTimeField(null=True, blank=True, editable=False)
    #: "Tout suspendre" : ni passage quotidien ni reprise automatique.
    automatismes_suspendus = models.BooleanField(default=False)
    #: Organisation de nuit (manage.py organiser) : une fois par jour a cette heure.
    heure_nuit = models.TimeField("heure de l'organisation de nuit", default=time(2, 0))
    #: Offres ajoutees apres cette date : pas encore reclassees par une nuit.
    nuit_depuis = models.DateTimeField(null=True, blank=True, editable=False)

    # Email du recapitulatif. Serveur vide : le .env s'applique (SMTP_HOST...).
    SECURITES_SMTP = [("tls", "STARTTLS"), ("ssl", "SSL/TLS"), ("aucune", "Aucune")]
    smtp_hote = models.CharField("serveur SMTP", max_length=255, blank=True)
    smtp_port = models.PositiveIntegerField("port SMTP", default=587)
    smtp_securite = models.CharField("sécurité SMTP", max_length=10,
                                     choices=SECURITES_SMTP, default="tls")
    smtp_utilisateur = models.CharField("utilisateur SMTP", max_length=255, blank=True)
    #: En clair en base, comme dans le .env. Jamais renvoye a l'ecran.
    smtp_mot_de_passe = models.CharField(max_length=255, blank=True, editable=False)
    #: Separes par des virgules. Vide : NOTIFY_TO du .env.
    destinataires = models.TextField("destinataires du récapitulatif", blank=True)

    #: Ponderation du score de correspondance (points sur 100), reglable a l'ecran.
    POIDS_DEFAUT = {"competences": 40, "domaine": 25, "categorie": 15,
                    "localisation": 15, "mots_cles": 5}
    poids = models.JSONField("pondération du score", default=dict, blank=True)
    #: Offres ajoutees apres cette date : pas encore passees au crible des alertes.
    alertes_depuis = models.DateTimeField(null=True, blank=True, editable=False)

    #: Au-dela, le planificateur est tenu pour arrete.
    SILENCE_MAX = timedelta(minutes=3)

    class Meta:
        db_table = "parametres"
        verbose_name = verbose_name_plural = "paramètres"

    def __str__(self):
        return "Paramètres"

    @classmethod
    def charger(cls):
        return cls.objects.get_or_create(pk=1)[0]

    @property
    def planificateur_actif(self) -> bool:
        return bool(self.planificateur_vu_le
                    and timezone.now() - self.planificateur_vu_le < self.SILENCE_MAX)

    def ponderation(self) -> dict:
        return {**self.POIDS_DEFAUT, **(self.poids or {})}

    def liste_destinataires(self) -> list:
        return [a for a in re.split(r"[,;\s]+", self.destinataires) if a]


class Secteur(models.Model):
    """Catalogue modifiable des secteurs proposés dans les offres et par l'IA."""

    code = models.SlugField(max_length=100, unique=True, db_index=True)
    nom = models.CharField("nom affiché", max_length=100)
    actif = models.BooleanField(default=True, db_index=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "secteurs"
        ordering = ["nom", "code"]
        verbose_name = "secteur"
        verbose_name_plural = "secteurs"

    def __str__(self):
        return self.nom


class Pays(models.Model):
    """Catalogue des pays et libellés de localisation présents dans les offres."""

    code = models.SlugField(max_length=100, unique=True, db_index=True)
    nom = models.CharField("nom affiché", max_length=100)
    actif = models.BooleanField(default=True, db_index=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pays_catalogue"
        ordering = ["nom", "code"]
        verbose_name = "pays"
        verbose_name_plural = "pays"

    def __str__(self):
        return self.nom


# --- Profils utilisateurs -------------------------------------------------
# Domaines et secteurs = catalogue Secteur (ce que portent les offres) ;
# Categorie et Competence completent pour la recherche fine.

class Categorie(models.Model):
    """Catégories de recherche, gérées par l'admin (ex. Développement web)."""

    code = models.SlugField(max_length=100, unique=True)
    nom = models.CharField("nom affiché", max_length=100)
    actif = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "categories"
        ordering = ["nom"]
        verbose_name = "catégorie de recherche"
        verbose_name_plural = "catégories de recherche"

    def __str__(self):
        return self.nom


class Competence(models.Model):
    """Compétences saisies par les utilisateurs ; une seule ligne par nom, casse comprise."""

    nom = models.CharField(max_length=80)

    class Meta:
        db_table = "competences"
        ordering = ["nom"]
        constraints = [models.UniqueConstraint(Lower("nom"), name="competence_nom_unique")]

    def __str__(self):
        return self.nom


def _chemin_prive(dossier, instance, nom):
    # Nom aleatoire : celui du fichier envoye n'est jamais repris tel quel sur disque.
    return f"{dossier}/{instance.user_id}/{uuid4().hex}{os.path.splitext(nom)[1].lower()}"


def chemin_cv(instance, nom):
    return _chemin_prive("cv", instance, nom)


def chemin_photo(instance, nom):
    return _chemin_prive("photos", instance, nom)


class Profil(models.Model):
    """Sections A à D du profil. Créé à la première visite de /profil/."""

    NIVEAUX = [("bac", "Bac"), ("bac2", "Bac+2"), ("bac3", "Bac+3 / Licence"),
               ("bac5", "Bac+5 / Master"), ("doctorat", "Doctorat"), ("autre", "Autre")]
    CONTRATS = [("cdi", "CDI"), ("cdd", "CDD"), ("consultant", "Consultant / freelance"),
                ("stage", "Stage"), ("alternance", "Alternance"), ("volontariat", "Volontariat")]
    DISPONIBILITES = [("immediate", "Immédiate"), ("1mois", "Sous 1 mois"),
                      ("3mois", "Sous 3 mois"), ("a_discuter", "À discuter")]
    MODES = [("site", "Sur site"), ("teletravail", "Télétravail"), ("hybride", "Hybride")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="profil")
    # A. Informations personnelles (prenom, nom, email : sur le compte)
    telephone = models.CharField("téléphone", max_length=20, blank=True, validators=[
        RegexValidator(r"^\+?[0-9 ().-]{6,20}$", "Numéro illisible : chiffres, espaces, + ( ) - .")])
    adresse = models.CharField(max_length=255, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    region = models.CharField("région", max_length=100, blank=True)
    code_postal = models.CharField(max_length=12, blank=True)
    pays = models.ForeignKey(Pays, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="+")
    photo = models.FileField(upload_to=chemin_photo, blank=True)
    date_naissance = models.DateField("date de naissance", null=True, blank=True)
    # B. Informations professionnelles
    titre = models.CharField("titre professionnel", max_length=150, blank=True)
    description = models.TextField("description personnelle", blank=True)
    annees_experience = models.PositiveSmallIntegerField(
        "années d'expérience", null=True, blank=True, validators=[MaxValueValidator(60)])
    niveau_etudes = models.CharField("niveau d'études", max_length=20, choices=NIVEAUX, blank=True)
    type_contrat = models.CharField("type de contrat recherché", max_length=20,
                                    choices=CONTRATS, blank=True)
    disponibilite = models.CharField("disponibilité", max_length=20,
                                     choices=DISPONIBILITES, blank=True)
    mode_travail = models.CharField("mode de travail souhaité", max_length=20,
                                    choices=MODES, blank=True)
    # C. Domaines et compétences
    secteurs = models.ManyToManyField(Secteur, blank=True, related_name="+",
                                      verbose_name="domaines et secteurs")
    categories = models.ManyToManyField(Categorie, blank=True, related_name="+",
                                        verbose_name="catégories de recherche")
    competences = models.ManyToManyField(Competence, blank=True, related_name="profils")
    mots_cles = models.CharField("mots-clés", max_length=500, blank=True)
    # D. CV (stockage prive : jamais servi par une URL publique)
    cv = models.FileField(upload_to=chemin_cv, blank=True)
    cv_nom = models.CharField(max_length=255, blank=True)
    cv_depose_le = models.DateTimeField(null=True, blank=True)
    #: Pages dont le guide pas a pas a ete vu ou passe (noms d'URL) : il ne revient pas.
    guides_vus = models.JSONField(default=list, blank=True, editable=False)
    maj_le = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profils"

    def __str__(self):
        return f"Profil de {self.user}"

    @classmethod
    def de(cls, user):
        return cls.objects.get_or_create(user=user)[0]

    def completion(self) -> int:
        """Part des éléments clés renseignés, en %."""
        u = self.user
        points = [u.first_name, u.last_name, self.telephone, self.ville, self.pays_id,
                  self.titre, self.description, self.niveau_etudes,
                  self.secteurs.exists(), self.competences.exists(), self.cv]
        return round(100 * sum(map(bool, points)) / len(points))


class Preferences(models.Model):
    """Section E : ce que l'utilisateur veut recevoir. Les domaines, compétences
    et mots-clés viennent du profil (section C), sans double saisie."""

    TYPES = [("marche", "Marchés"), ("emploi", "Postes")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="preferences")
    pays = models.ManyToManyField(Pays, blank=True, related_name="+",
                                  verbose_name="pays de recherche")
    #: Codes de services.geo (afrique, europe...).
    regions = models.JSONField(default=list, blank=True)
    villes = models.CharField(max_length=255, blank=True)
    #: Vide : marchés et postes.
    types_offres = models.JSONField(default=list, blank=True)
    teletravail = models.BooleanField("télétravail accepté", default=False)
    notifications = models.BooleanField("notifications activées", default=True)
    #: Score minimal (0-100) d'une offre pour etre suggeree ou notifiee.
    seuil = models.PositiveSmallIntegerField("seuil de pertinence", default=40,
                                             validators=[MaxValueValidator(100)])

    class Meta:
        db_table = "preferences"
        verbose_name = verbose_name_plural = "préférences"

    def __str__(self):
        return f"Préférences de {self.user}"

    @classmethod
    def de(cls, user):
        return cls.objects.get_or_create(user=user)[0]


class Notification(models.Model):
    """Une offre signalée à un utilisateur. L'unicité (user, offre) garantit
    qu'une même offre n'est jamais notifiée deux fois à la même personne."""

    EN_ATTENTE, ENVOYEE, ECHEC = "pending", "sent", "failed"
    STATUTS = [(EN_ATTENTE, "En attente"), (ENVOYEE, "Envoyée"), (ECHEC, "Échec")]
    #: Au-dela, l'envoi n'est plus retente (erreur conservee pour l'admin).
    TENTATIVES_MAX = 3

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="notifications")
    offre = models.ForeignKey(Offre, on_delete=models.CASCADE, related_name="+")
    score = models.PositiveSmallIntegerField()
    statut = models.CharField(max_length=10, choices=STATUTS, default=EN_ATTENTE, db_index=True)
    tentatives = models.PositiveSmallIntegerField(default=0)
    erreur = models.TextField(blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    envoye_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-cree_le"]
        constraints = [models.UniqueConstraint(fields=["user", "offre"],
                                               name="notification_unique")]

    def __str__(self):
        return f"{self.user} · {self.offre_id} · {self.get_statut_display()}"


class Plan(models.Model):
    """Offre d'abonnement, modifiable dans l'admin. Paiement hors ligne :
    l'utilisateur demande, un admin valide à la main."""

    nom = models.CharField(max_length=60)
    prix = models.DecimalField("prix (€)", max_digits=8, decimal_places=2,
                               validators=[MinValueValidator(0)])
    credits = models.PositiveIntegerField("crédits")
    par_jour = models.BooleanField(
        "crédits chaque jour", default=False,
        help_text="Coché : les crédits sont disponibles chaque jour de la période. "
                  "Décoché : un lot unique, utilisé une fois les crédits du jour épuisés.")
    duree_jours = models.PositiveSmallIntegerField(
        "durée (jours)", null=True, blank=True,
        help_text="Vide : sans fin (lot utilisable jusqu'à épuisement).")
    actif = models.BooleanField("proposé", default=True)

    class Meta:
        db_table = "plans"
        ordering = ["prix"]

    def __str__(self):
        return f"{self.nom} ({self.prix} €)"

    @property
    def prix_credit(self) -> Decimal:
        """Coût d'un crédit, pour comparer les plans (€, 4 décimales : souvent moins d'un centime)."""
        total = self.credits * ((self.duree_jours or 1) if self.par_jour else 1)
        return (Decimal(self.prix) / total).quantize(Decimal("0.0001")) if total else Decimal(0)


class Abonnement(models.Model):
    """Demande d'un plan par un utilisateur. Les crédits sont copiés du plan à la
    validation : modifier un plan ne change pas les abonnements déjà validés."""

    EN_ATTENTE, VALIDE, REFUSE = "attente", "valide", "refuse"
    STATUTS = [(EN_ATTENTE, "En attente"), (VALIDE, "Validé"), (REFUSE, "Refusé")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="abonnements")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="abonnements")
    statut = models.CharField(max_length=10, choices=STATUTS, default=EN_ATTENTE, db_index=True)
    demande_le = models.DateTimeField(auto_now_add=True)
    debut = models.DateField(null=True, blank=True)
    fin = models.DateField(null=True, blank=True, help_text="Dernier jour inclus ; vide = sans fin.")
    credits_jour = models.PositiveIntegerField("crédits par jour", default=0)
    credits_restants = models.PositiveIntegerField("crédits du lot restants", default=0)
    valide_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="+")

    class Meta:
        db_table = "abonnements"
        ordering = ["-demande_le"]

    def __str__(self):
        return f"{self.user} · {self.plan.nom} · {self.get_statut_display()}"

    def valider(self, par):
        jour = timezone.localdate()
        self.statut, self.debut, self.valide_par = self.VALIDE, jour, par
        self.fin = jour + timedelta(days=self.plan.duree_jours - 1) if self.plan.duree_jours else None
        if self.plan.par_jour:
            self.credits_jour = self.plan.credits
        else:
            self.credits_restants = self.plan.credits
        self.save()

    def refuser(self):
        self.statut = self.REFUSE
        self.save(update_fields=["statut"])

    @classmethod
    def actifs(cls, user, jour=None):
        jour = jour or timezone.localdate()
        return cls.objects.filter(Q(fin__isnull=True) | Q(fin__gte=jour),
                                  user=user, statut=cls.VALIDE, debut__lte=jour)


class Inscription(models.Model):
    """Création d'un compte : fin de l'essai gratuit et empreintes anti-multicomptes.
    IP et appareil sont gardés en HMAC (voir inscription.py), jamais en clair."""

    #: Durée de l'essai gratuit (consultations illimitées). Aussi écrite dans les textes du frontend.
    ESSAI_JOURS = 14

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="inscription")
    essai_jusqu_au = models.DateField("essai gratuit jusqu'au", null=True, blank=True,
                                      help_text="Dernier jour inclus ; vide = pas d'essai.")
    ip = models.CharField("empreinte de l'IP", max_length=64, blank=True, db_index=True)
    appareil = models.CharField("empreinte de l'appareil", max_length=64, blank=True, db_index=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inscriptions"

    def __str__(self):
        return f"{self.user} · essai jusqu'au {self.essai_jusqu_au or '—'}"

    @classmethod
    def essai(cls, user):
        """Dernier jour de l'essai gratuit s'il est en cours, sinon None."""
        fin = cls.objects.filter(user=user).values_list("essai_jusqu_au", flat=True).first()
        return fin if fin and fin >= timezone.localdate() else None


class Consultation(models.Model):
    """Une annonce officielle ouverte par un utilisateur, un jour donné.
    Unicité (user, offre, jour) : rouvrir la même offre le même jour ne coûte rien.
    Pendant l'essai gratuit, rien n'est décompté ; ensuite, seuls les abonnements donnent des crédits."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="consultations")
    offre = models.ForeignKey(Offre, on_delete=models.CASCADE, related_name="+")
    jour = models.DateField(default=timezone.localdate)

    class Meta:
        db_table = "consultations"
        constraints = [models.UniqueConstraint(fields=["user", "offre", "jour"],
                                               name="consultation_unique_par_jour")]

    @classmethod
    def du_jour(cls, user) -> tuple[int, int]:
        """(crédits du jour restants, crédits de lots restants)."""
        actifs = Abonnement.actifs(user)
        quota = actifs.aggregate(n=models.Sum("credits_jour"))["n"] or 0
        lots = actifs.aggregate(n=models.Sum("credits_restants"))["n"] or 0
        return max(0, quota - cls.objects.filter(user=user, jour=timezone.localdate()).count()), lots

    @classmethod
    def restantes(cls, user) -> int:
        return sum(cls.du_jour(user))

    @classmethod
    def debiter_verrouille(cls, user, offre) -> bool:
        """`debiter` dans une transaction, utilisateur verrouillé : deux clics
        simultanés ne dépassent pas la limite."""
        from django.contrib.auth import get_user_model
        from django.db import transaction
        with transaction.atomic():
            return cls.debiter(get_user_model().objects.select_for_update().get(pk=user.pk), offre)

    @classmethod
    def debiter(cls, user, offre) -> bool:
        """Enregistre l'ouverture de l'offre ; False si plus aucun crédit.
        À appeler dans une transaction, utilisateur verrouillé."""
        jour = timezone.localdate()
        if cls.objects.filter(user=user, offre=offre, jour=jour).exists():
            return True
        if Inscription.essai(user):
            cls.objects.create(user=user, offre=offre, jour=jour)
            return True
        du_jour, _ = cls.du_jour(user)
        if not du_jour:
            # Lot qui expire le plus tôt d'abord ; les lots sans fin en dernier.
            lot = (Abonnement.actifs(user).filter(credits_restants__gt=0)
                   .order_by(models.F("fin").asc(nulls_last=True), "pk").first())
            if not lot:
                return False
            Abonnement.objects.filter(pk=lot.pk).update(credits_restants=models.F("credits_restants") - 1)
        cls.objects.create(user=user, offre=offre, jour=jour)
        return True
