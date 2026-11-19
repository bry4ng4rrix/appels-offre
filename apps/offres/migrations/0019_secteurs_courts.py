"""Raccourcit les secteurs crees par Gemma a trois mots-cles au plus.

"Autres services clients services clients activities services publics" et ses
variantes deviennent "Autres services clients" ; leurs offres suivent.
"""

from django.db import migrations

from apps.offres.services.taxonomie import raccourcir_secteurs


def raccourcir(apps, schema_editor):
    raccourcir_secteurs(apps.get_model("offres", "Secteur"), apps.get_model("offres", "Offre"))


class Migration(migrations.Migration):

    dependencies = [("offres", "0018_guides_vus")]

    operations = [migrations.RunPython(raccourcir, migrations.RunPython.noop)]
