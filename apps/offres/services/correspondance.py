"""Correspondance entre une offre et un profil : critères, score, suggestions.

Le score (0-100) pondère cinq critères (onglet Paramètres > Pertinence) :
compétences, domaine (secteur de l'offre), catégorie, localisation, mots-clés.
Seuls les critères que l'utilisateur a renseignés comptent : un profil qui
n'a donné que son pays et ses secteurs n'est pas pénalisé de ses compétences vides.

Filtre par défaut : sans pays ni région de recherche, on prend le pays de
résidence du profil et sa région.
"""

from dataclasses import dataclass, field
from datetime import date

from django.db.models import Q
from django.utils import timezone

from apps.offres.models import Offre, Parametres, Preferences, Profil
from apps.offres.services import geo

#: Texte d'une offre examine (titre + debut de description) : borne le cout.
LONGUEUR_TEXTE = 1200
#: Trois competences trouvees suffisent pour le plein de points.
COMPETENCES_PLEINES = 3
TELETRAVAIL = ("teletravail", "remote", "home based", "work from home", "a distance")


@dataclass
class Criteres:
    pays: set = field(default_factory=set)       # lieux normalises (Offre.pays est libre)
    regions: set = field(default_factory=set)    # codes de services.geo
    secteurs: set = field(default_factory=set)
    categories: list = field(default_factory=list)
    competences: list = field(default_factory=list)
    mots_cles: list = field(default_factory=list)
    types: list = field(default_factory=list)
    teletravail: bool = False
    seuil: int = 40

    @property
    def vide(self) -> bool:
        return not (self.pays or self.regions or self.secteurs or self.categories
                    or self.competences or self.mots_cles)


def _termes(texte: str) -> list:
    return [t for t in (geo.normaliser(m) for m in (texte or "").split(",")) if t]


def criteres(user) -> Criteres:
    profil, prefs = Profil.de(user), Preferences.de(user)
    pays = {geo.normaliser(p.nom) for p in prefs.pays.all()}
    regions = set(prefs.regions or [])
    villes = set(_termes(prefs.villes))
    if not (pays or regions or villes) and profil.pays_id:
        # Filtre par defaut : le pays de residence et sa region.
        pays = {geo.normaliser(profil.pays.nom)}
        regions = {geo.region(profil.pays.nom)} - {geo.INCONNUE}
    return Criteres(
        pays=pays | villes, regions=regions,
        secteurs=set(profil.secteurs.values_list("code", flat=True)),
        categories=[geo.normaliser(n) for n in profil.categories.values_list("nom", flat=True)],
        competences=[geo.normaliser(n) for n in profil.competences.values_list("nom", flat=True)],
        mots_cles=_termes(profil.mots_cles), types=list(prefs.types_offres or []),
        teletravail=prefs.teletravail, seuil=prefs.seuil)


def _contient(texte: str, terme: str) -> bool:
    # Mot entier : « java » ne doit pas trouver « javascript ».
    return f" {terme} " in texte


def score(offre, c: Criteres, poids=None) -> int:
    if c.vide:
        return 0
    poids = poids or Parametres.charger().ponderation()
    texte = " " + geo.normaliser(" ".join(filter(None, (
        offre.titre, offre.categorie, offre.organisation,
        (offre.description or "")[:LONGUEUR_TEXTE])))) + " "
    lieu = geo.normaliser(offre.pays)

    obtenus, possibles = 0.0, 0
    if c.competences:
        trouvees = sum(_contient(texte, t) for t in c.competences)
        obtenus += poids["competences"] * min(1, trouvees / min(COMPETENCES_PLEINES, len(c.competences)))
        possibles += poids["competences"]
    if c.secteurs:
        obtenus += poids["domaine"] * (offre.secteur in c.secteurs)
        possibles += poids["domaine"]
    if c.categories:
        obtenus += poids["categorie"] * any(_contient(texte, t) for t in c.categories)
        possibles += poids["categorie"]
    if c.pays or c.regions:
        ici = (lieu in c.pays) or (geo.region(offre.pays) in c.regions)
        a_distance = c.teletravail and any(_contient(texte, t) for t in TELETRAVAIL)
        obtenus += poids["localisation"] * (ici or a_distance)
        possibles += poids["localisation"]
    if c.mots_cles:
        obtenus += poids["mots_cles"] * any(_contient(texte, t) for t in c.mots_cles)
        possibles += poids["mots_cles"]
    return round(100 * obtenus / possibles) if possibles else 0


def ouvertes():
    """Offres encore ouvertes, retenues ou non : le tri « retenue » sert l'équipe
    commerciale, pas les métiers des utilisateurs."""
    aujourdhui = timezone.now().date()
    return Offre.objects.exclude(Q(date_limite__lt=aujourdhui) | Q(lien_etat__in=Offre.LIEN_FERME))


def suggestions(user, lot=None) -> tuple:
    """(critères, offres au-dessus du seuil triées par score) ; chaque offre porte `.score`."""
    c = criteres(user)
    if c.vide:
        return c, []
    lot = lot if lot is not None else ouvertes()
    if c.types:
        lot = lot.filter(nature__in=c.types)
    poids = Parametres.charger().ponderation()
    retenues = []
    for offre in lot.only("id", "source", "titre", "organisation", "pays", "description",
                          "categorie", "secteur", "nature", "date_limite", "lien",
                          "lien_etat", "date_publication", "date_ajout"):
        offre.score = score(offre, c, poids)
        if offre.score >= c.seuil:
            retenues.append(offre)
    # Meilleur score d'abord ; a score egal, l'echeance la plus proche.
    retenues.sort(key=lambda o: (-o.score, o.date_limite or date.max))
    return c, retenues
