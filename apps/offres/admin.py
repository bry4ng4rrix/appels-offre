"""Interface d'administration des offres.

Pensee pour la consultation et la validation a la main, pas pour la saisie :
les offres viennent du pipeline. Les champs issus de la collecte sont donc en
lecture seule -- ils viennent des scrapers et
ne se corrigent pas a la main. Seuls `pertinent` et `categorie`
sont modifiables : ce sont des verdicts, qu'un humain peut vouloir corriger.
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import CleApi, Offre, Suivi


class EcheanceFilter(admin.SimpleListFilter):
    """Filtre par urgence plutot que par date brute.

    Une date exacte n'aide pas a decider : ce qu'on veut savoir, c'est ce qui
    ferme bientot et ce qui est encore ouvert.
    """

    title = "échéance"
    parameter_name = "echeance"

    #: Applique tant que l'utilisateur n'a rien choisi. Une offre cloturee
    #: n'est plus actionnable : l'afficher par defaut noie les autres.
    DEFAUT = "ouvert"

    def lookups(self, request, model_admin):
        return [
            ("7", "Clôture sous 7 jours"),
            ("30", "Clôture sous 30 jours"),
            ("ouvert", "Encore ouverte (défaut)"),
            ("clos", "Clôturée"),
            ("sans", "Sans date limite"),
            ("toutes", "Toutes, clôturées comprises"),
        ]

    def choices(self, changelist):
        """Marque le defaut comme selectionne plutot que « Tout ».

        Sans cela l'entete afficherait « Tout » alors qu'un filtre s'applique
        -- l'utilisateur croirait voir l'integralite des offres.
        """
        for choix in super().choices(changelist):
            if choix["query_string"] == "?":
                continue          # masque l'entree « Tout », trompeuse ici
            yield choix

    def queryset(self, request, queryset):
        aujourdhui = timezone.now().date()
        valeur = self.value() or self.DEFAUT
        if valeur == "toutes":
            return queryset
        if valeur in {"7", "30"}:
            from datetime import timedelta
            limite = aujourdhui + timedelta(days=int(valeur))
            return queryset.filter(date_limite__gte=aujourdhui, date_limite__lte=limite)
        if valeur == "ouvert":
            # Une offre SANS date limite doit rester visible : on ne peut pas
            # affirmer qu'elle est close. Toute la source BAD est dans ce cas
            # (l'echeance est dans le PDF, pas dans la liste) -- l'exclure
            # rendrait cette source entierement invisible dans l'admin.
            from django.db.models import Q
            return queryset.filter(Q(date_limite__gte=aujourdhui)
                                   | Q(date_limite__isnull=True))
        if valeur == "clos":
            return queryset.filter(date_limite__lt=aujourdhui)
        if valeur == "sans":
            return queryset.filter(date_limite__isnull=True)
        return queryset


class PertinenceFilter(admin.SimpleListFilter):
    """Retenues par defaut : les ecartees restent consultables a la demande.

    Elles sont conservees en base exprès -- elles permettent d'auditer un
    changement de criteres de tri sans re-scraper. Mais elles n'ont rien a
    faire dans la vue de travail quotidienne.
    """

    title = "pertinence"
    parameter_name = "retenue"
    DEFAUT = "oui"

    def lookups(self, request, model_admin):
        return [("oui", "Retenues (défaut)"), ("non", "Écartées"),
                ("toutes", "Toutes")]

    def choices(self, changelist):
        for choix in super().choices(changelist):
            if choix["query_string"] == "?":
                continue
            yield choix

    def queryset(self, request, queryset):
        valeur = self.value() or self.DEFAUT
        if valeur == "oui":
            return queryset.filter(pertinent=True)
        if valeur == "non":
            return queryset.filter(pertinent=False)
        return queryset


class NatureFilter(admin.SimpleListFilter):
    """Marches contre postes salaries.

    Sans defaut impose, contrairement aux filtres de pertinence et
    d'echeance : les deux natures interessent, mais pas au meme moment.
    "Non qualifiee" reste accessible -- ce sont les offres jugees avant que la
    distinction n'existe.
    """

    title = "nature"
    parameter_name = "nature_offre"

    def lookups(self, request, model_admin):
        return (("marche", "Marchés"), ("emploi", "Postes salariés"),
                ("inconnue", "Non qualifiée"))

    def queryset(self, request, queryset):
        valeur = self.value()
        if valeur == "inconnue":
            return queryset.filter(nature__isnull=True)
        if valeur in ("marche", "emploi"):
            return queryset.filter(nature=valeur)
        return queryset


@admin.register(Offre)
class OffreAdmin(admin.ModelAdmin):
    list_display = ("titre_court", "secteur", "nature", "source",
                    "organisation", "pays", "echeance", "pertinent")
    list_filter = (PertinenceFilter, EcheanceFilter, "secteur", NatureFilter,
                   "source", "categorie")
    search_fields = ("titre", "organisation", "pays", "categorie", "description")
    list_per_page = 50
    date_hierarchy = "date_ajout"

    # Le pipeline est proprietaire de ces champs : les rendre editables
    # laisserait croire qu'une correction survit au prochain chargement.
    readonly_fields = ("id", "source", "titre", "organisation", "pays",
                       "date_limite", "lien_cliquable", "description",
                       "raison", "date_ajout", "date_maj")
    fields = ("titre", "source", "organisation", "pays", "date_limite",
              "lien_cliquable", "pertinent", "secteur", "nature", "categorie",
              "raison",
              "description", "date_ajout", "date_maj")

    actions = ("marquer_pertinent", "marquer_non_pertinent")

    @admin.display(description="titre", ordering="titre")
    def titre_court(self, obj):
        return obj.titre[:80] + ("…" if len(obj.titre) > 80 else "")

    @admin.display(description="échéance", ordering="date_limite")
    def echeance(self, obj):
        restants = obj.jours_restants
        if restants is None:
            return "—"
        if restants < 0:
            # format_html exige au moins un argument depuis Django 5 : appele a
            # vide, il leve TypeError. Le libelle passe donc en parametre.
            return format_html('<span style="color:#888">{}</span>', "clôturée")
        if restants <= 7:
            return format_html('<b style="color:#c00">dans {} j</b>', restants)
        return f"dans {restants} j"

    @admin.display(description="lien")
    def lien_cliquable(self, obj):
        if not obj.lien:
            return "—"
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>',
                           obj.lien, obj.lien)

    @admin.action(description="Marquer comme retenue")
    def marquer_pertinent(self, request, queryset):
        n = queryset.update(pertinent=True, date_maj=timezone.now())
        self.message_user(request, f"{n} offre(s) marquée(s) comme retenue(s).")

    @admin.action(description="Marquer comme écartée")
    def marquer_non_pertinent(self, request, queryset):
        n = queryset.update(pertinent=False, date_maj=timezone.now())
        self.message_user(request, f"{n} offre(s) marquée(s) comme écartée(s).")


@admin.register(CleApi)
class CleApiAdmin(admin.ModelAdmin):
    """Les cles se consultent et se revoquent ici, elles se creent en ligne
    de commande : `manage.py cle_api --creer <nom>`.

    Le jeton n'apparait nulle part -- seule son empreinte est conservee. Il
    n'y a donc rien a lire ici qui donne un acces.
    """

    list_display = ("nom", "etat", "cree_le", "derniere_utilisation")
    list_filter = ("revoque_le",)
    search_fields = ("nom",)
    readonly_fields = ("empreinte", "cree_le", "derniere_utilisation")
    fields = ("nom", "empreinte", "cree_le", "derniere_utilisation", "revoque_le")

    @admin.display(description="état", boolean=True)
    def etat(self, obj):
        return obj.active

    def has_add_permission(self, request):
        # Ajouter depuis l'admin creerait une ligne sans jeton utilisable :
        # l'empreinte ne peut pas etre saisie a la main.
        return False

    actions = ("revoquer",)

    @admin.action(description="Révoquer les clés sélectionnées")
    def revoquer(self, request, queryset):
        from django.utils import timezone
        n = queryset.filter(revoque_le__isnull=True).update(
            revoque_le=timezone.now())
        self.message_user(request, f"{n} clé(s) révoquée(s).")


@admin.register(Suivi)
class SuiviAdmin(admin.ModelAdmin):
    """Le suivi commercial, pour les corrections en lot.

    La saisie courante se fait au bas de la fiche d'une offre, ou le contexte
    est sous les yeux. Cet ecran sert a relire l'ensemble, corriger une
    erreur, ou reprendre les decisions d'un compte supprime.
    """

    list_display = ("offre", "statut", "note", "decide_par", "decide_par_cle", "maj_le")
    list_filter = ("statut", "decide_par", "decide_par_cle")
    search_fields = ("offre__titre", "note")
    list_select_related = ("offre", "decide_par", "decide_par_cle")
    # La date de derniere decision se lit, elle ne se saisit pas.
    readonly_fields = ("cree_le", "maj_le")
    date_hierarchy = "maj_le"
