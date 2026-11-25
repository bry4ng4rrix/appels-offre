"""Les trois plans de départ ; ensuite modifiables dans l'admin."""

from django.db import migrations

PLANS = [
    dict(nom="Standard", prix=5000, credits=20, par_jour=False, duree_jours=None),
    dict(nom="Mensuel", prix=65000, credits=50, par_jour=True, duree_jours=30),
    dict(nom="Deux mois", prix=105000, credits=100, par_jour=True, duree_jours=60),
]


def creer(apps, schema_editor):
    Plan = apps.get_model("offres", "Plan")
    for plan in PLANS:
        Plan.objects.get_or_create(nom=plan["nom"], defaults=plan)


class Migration(migrations.Migration):

    dependencies = [("offres", "0021_abonnements")]

    operations = [migrations.RunPython(creer, migrations.RunPython.noop)]
