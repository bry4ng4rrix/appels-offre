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
}


#: Un secteur se lit d'un coup d'oeil : trois mots-cles au plus. Gemma proposait
#: des codes de 80 caracteres qui se repetaient ("autres_services_clients_services_
#: clients_activities_services_publics_services_tec").
MOTS_MAX_SECTEUR = 3


def code_secteur(valeur: str) -> str:
    """Produit un code stable et court, et rabat les synonymes sur le secteur canonique."""
    code = slugify((valeur or "").strip(), allow_unicode=False).replace("-", "_")
    mots = list(dict.fromkeys(m for m in code.split("_") if m))   # sans doublons, ordre garde
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
        if Secteur.objects.filter(code=court).exists():
            secteur.delete()
        else:
            Secteur.objects.filter(pk=secteur.pk).update(code=court, nom=nom)
        raccourcis += 1
    return raccourcis


def code_pays(valeur: str) -> str:
    """Produit une clé stable pour rapprocher accents et ponctuation des lieux."""
    return slugify(normaliser_lieu(valeur), allow_unicode=False)[:100]
