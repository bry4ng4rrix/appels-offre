"""Organisation de nuit : ranger les catalogues, puis mieux classer les nouvelles offres.

Lancée une fois par nuit par le planificateur (heure réglable dans Paramètres),
à part du traitement complet des 6 heures, qui ne fait que trier vite.

1. Catalogues
   - secteurs synonymes rabattus sur le secteur canonique (« electricity » -> « energie ») ;
   - secteurs portés par des offres mais absents du catalogue : inscrits ;
   - catégories recalculées après un renommage de secteur (« <Secteur> - <Nature> ») ;
   - lieux des offres ajoutés au catalogue des pays.
2. Classement
   Les offres arrivées depuis la nuit précédente, et les offres encore ouvertes
   restées « autre », repassent au classifieur complet. La nuit laisse à Gemma
   (CLASSIFICATEUR_IA=ollama) le temps que la collecte de jour ne lui donne pas.
"""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.offres.models import Offre, Parametres, Secteur
from apps.offres.services.correspondance import ouvertes
from apps.offres.services.pays import synchroniser_pays
from apps.offres.services.pipeline import PipelineService
from apps.offres.services.taxonomie import code_secteur, raccourcir_secteurs

#: Premiere nuit : on remonte d'une journee.
PREMIERE_NUIT = timedelta(hours=24)
#: Offres « autre » reprises par nuit : borne la duree des appels a Gemma.
# shortcut: une offre que Gemma ne sait pas classer est retentee chaque nuit (300 au plus) ;
# memoriser ces echecs si la nuit devient trop longue.
LIMITE_AUTRES = 300


def catalogues(progression) -> dict:
    progression(etape="Synonymes de secteurs")
    fusionnes = 0
    for code in Offre.objects.exclude(secteur__isnull=True).exclude(secteur="") \
                             .values_list("secteur", flat=True).distinct():
        canonique = code_secteur(code)
        if canonique and canonique != code:
            fusionnes += Offre.objects.filter(secteur=code).update(secteur=canonique)

    progression(etape="Catalogue des secteurs")
    raccourcir_secteurs(Secteur, Offre)
    connus = set(Secteur.objects.values_list("code", flat=True))
    portes = set(Offre.objects.exclude(secteur__isnull=True).exclude(secteur__in=["", "autre"])
                 .values_list("secteur", flat=True).distinct())
    nouveaux = [Secteur(code=c, nom=c.replace("_", " ").capitalize()) for c in sorted(portes - connus)]
    Secteur.objects.bulk_create(nouveaux, ignore_conflicts=True)

    progression(etape="Catégories")
    renommees = 0
    for secteur in Secteur.objects.filter(actif=True):
        for nature in ("marche", "emploi"):
            attendue = f"{secteur.nom} - {nature.capitalize()}"
            renommees += (Offre.objects.filter(secteur=secteur.code, nature=nature)
                          .exclude(categorie=attendue).update(categorie=attendue))

    progression(etape="Catalogue des pays")
    synchroniser_pays(Offre.objects.exclude(pays__isnull=True).exclude(pays="")
                      .values_list("pays", flat=True).distinct())
    return {"fusionnes": fusionnes, "secteurs_ajoutes": len(nouveaux), "categories": renommees}


def a_classer(debut_tache):
    """Nouvelles depuis la nuit precedente + ouvertes encore « autre ».
    Celles deja reclassees par cette tache (reprise apres coupure) sont sautees."""
    reglages = Parametres.charger()
    depuis = reglages.nuit_depuis or timezone.now() - PREMIERE_NUIT
    autres = list(ouvertes().filter(Q(secteur__isnull=True) | Q(secteur__in=["", "autre"]))
                  .order_by("-date_ajout").values_list("pk", flat=True)[:LIMITE_AUTRES])
    lot = Offre.objects.filter(Q(date_ajout__gt=depuis) | Q(pk__in=autres))
    if debut_tache:
        lot = lot.exclude(trie_le__gte=debut_tache)
    return lot


def classer(progression) -> dict:
    debut = timezone.now()
    resultat = PipelineService.requalifier(a_classer(progression.debut), progression)
    Parametres.objects.filter(pk=Parametres.charger().pk).update(nuit_depuis=debut)
    return resultat
