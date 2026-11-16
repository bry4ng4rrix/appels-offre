from django.db import migrations


ALIASES = {
    "electrical": "energie",
    "electricite": "energie",
    "electricity": "energie",
    "energy": "energie",
    "ecologie": "environnement",
    "ecology": "environnement",
}


def fusionner_secteurs(apps, schema_editor):
    alias_db = schema_editor.connection.alias
    Offre = apps.get_model("offres", "Offre")
    Secteur = apps.get_model("offres", "Secteur")
    libelles = {"energie": "Energie", "environnement": "Environnement"}

    for alias, canonique in ALIASES.items():
        offres = Offre.objects.using(alias_db).filter(secteur=alias).only("id", "nature")
        lot = []
        for offre in offres.iterator(chunk_size=500):
            offre.secteur = canonique
            nature = "Emploi" if offre.nature == "emploi" else "Marche"
            offre.categorie = f"{libelles[canonique]} - {nature}"
            lot.append(offre)
            if len(lot) == 500:
                Offre.objects.using(alias_db).bulk_update(lot, ["secteur", "categorie"])
                lot = []
        if lot:
            Offre.objects.using(alias_db).bulk_update(lot, ["secteur", "categorie"])

        Secteur.objects.using(alias_db).filter(code=canonique).update(actif=True)
        Secteur.objects.using(alias_db).filter(code=alias).delete()


class Migration(migrations.Migration):
    dependencies = [("offres", "0010_catalogue_secteurs")]

    operations = [
        migrations.RunPython(fusionner_secteurs, migrations.RunPython.noop),
    ]
