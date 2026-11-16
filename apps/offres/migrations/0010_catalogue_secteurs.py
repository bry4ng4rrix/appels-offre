from django.db import migrations, models


SECTEURS_INITIAUX = (
    "informatique", "eau", "environnement", "agriculture", "construction",
    "sante", "education", "transport", "energie", "finance", "gouvernance",
    "eau_et_assainissement", "developpement_social",
)


def remplir_catalogue(apps, schema_editor):
    Secteur = apps.get_model("offres", "Secteur")
    Offre = apps.get_model("offres", "Offre")
    codes = set(SECTEURS_INITIAUX)
    codes.update(
        Offre.objects.exclude(secteur__isnull=True).exclude(secteur="")
        .values_list("secteur", flat=True).distinct()
    )
    codes.discard("autre")
    Secteur.objects.bulk_create([
        Secteur(code=code[:100], nom=code.replace("_", " ").capitalize())
        for code in sorted(codes)
    ], ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [("offres", "0009_intervalle_collecte")]

    operations = [
        migrations.CreateModel(
            name="Secteur",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("code", models.SlugField(db_index=True, max_length=100, unique=True)),
                ("nom", models.CharField(max_length=100, verbose_name="nom affiché")),
                ("actif", models.BooleanField(db_index=True, default=True)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "secteur",
                "verbose_name_plural": "secteurs",
                "db_table": "secteurs",
                "ordering": ["nom", "code"],
            },
        ),
        migrations.RunPython(remplir_catalogue, migrations.RunPython.noop),
    ]
