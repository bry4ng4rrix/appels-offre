"""Normalisation des secteurs et des pays pour eviter les doublons."""

from django.utils.text import slugify

from .geo import normaliser as normaliser_lieu


EQUIVALENCES_SECTEURS = {
    "electrical": "energie",
    "electricite": "energie",
    "electricity": "energie",
    "energy": "energie",
    "ecologie": "environnement",
    "ecology": "environnement",
    # Gemma dit souvent « pas de secteur » autrement : ce n'est pas un nouveau secteur.
    "autres": "autre", "other": "autre", "others": "autre", "divers": "autre",
    "aucun": "autre", "none": "autre", "inconnu": "autre", "general": "autre",
    "non_classe": "autre", "non_classifie": "autre",
    # Le developpement rural est le meme secteur que l'agriculture.
    "agriculture_et_rural": "agriculture", "agriculture_rural": "agriculture",
    "agriculture_et_developpement": "agriculture",
}

#: Mot a mot, avant la coupe a trois mots : les sources et Gemma ecrivent le
#: meme secteur en anglais, en francais ou en adjectif. "Administrative and
#: support", "Administrative et support" et "Administration et support"
#: donnaient trois secteurs a l'ecran.
MOTS_EQUIVALENTS = {
    "and": "et", "administrative": "administration", "administratif": "administration",
    "agricultural": "agriculture", "agricole": "agriculture",
    "environment": "environnement", "environmental": "environnement",
    "environnemental": "environnement", "health": "sante", "water": "eau",
    "sanitation": "assainissement", "financial": "finance", "financier": "finance",
    "legal": "juridique", "technology": "technologie", "technologies": "technologie",
    "engineering": "ingenierie", "security": "securite", "humanitarian": "humanitaire",
    "management": "gestion", "transportation": "transport", "development": "developpement",
    "governance": "gouvernance", "research": "recherche", "quality": "qualite",
    "communications": "communication", "telecommunications": "telecommunication",
}


#: Un secteur se lit d'un coup d'oeil : trois mots-cles au plus. Gemma proposait
#: des codes de 80 caracteres qui se repetaient ("autres_services_clients_services_
#: clients_activities_services_publics_services_tec").
MOTS_MAX_SECTEUR = 3


def code_secteur(valeur: str) -> str:
    """Produit un code stable et court, et rabat les synonymes sur le secteur canonique."""
    code = slugify((valeur or "").strip(), allow_unicode=False).replace("-", "_")
    mots = list(dict.fromkeys(MOTS_EQUIVALENTS.get(m, m)
                              for m in code.split("_") if m))   # sans doublons, ordre garde
    code = "_".join(mots[:MOTS_MAX_SECTEUR])
    return EQUIVALENCES_SECTEURS.get(code, code)


def raccourcir_secteurs(Secteur, Offre) -> int:
    """Ramene chaque secteur du catalogue a son code court et y rattache ses offres.

    Prend les modeles en parametre : sert a la migration (modeles historiques)
    comme a l'organisation de nuit. Renvoie le nombre de secteurs raccourcis.
    """
    raccourcis = 0
    for secteur in list(Secteur.objects.all()):
        court = code_secteur(secteur.code)
        if not court or court == secteur.code:
            continue
        nom = court.replace("_", " ").capitalize()
        for nature in ("marche", "emploi"):
            Offre.objects.filter(secteur=secteur.code, nature=nature).update(
                secteur=court, categorie=f"{nom} - {nature.capitalize()}")
        Offre.objects.filter(secteur=secteur.code).update(secteur=court)
        canonique = Secteur.objects.filter(code=court).first()
        if canonique:
            _reporter_profils(Secteur, secteur, canonique)
            secteur.delete()
        else:
            Secteur.objects.filter(pk=secteur.pk).update(code=court, nom=nom)
        raccourcis += 1
    return raccourcis


def _reporter_profils(Secteur, ancien, nouveau) -> None:
    """Les profils qui avaient choisi le doublon gardent le secteur fusionne :
    sans ce report, supprimer le doublon effacerait leur choix."""
    try:
        Profil = Secteur._meta.apps.get_model("offres", "Profil")
    except LookupError:  # migration anterieure aux profils
        return
    Lien = Profil.secteurs.through
    Lien.objects.bulk_create(
        [Lien(profil_id=p, secteur_id=nouveau.pk) for p in
         Lien.objects.filter(secteur_id=ancien.pk).values_list("profil_id", flat=True)],
        ignore_conflicts=True)


def code_pays(valeur: str) -> str:
    """Produit une clé stable pour rapprocher accents et ponctuation des lieux."""
    return slugify(normaliser_lieu(valeur), allow_unicode=False)[:100]
