from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("offres", "0007_une_seule_tache_en_cours")]

    operations = [
        migrations.AlterField(
            model_name="offre",
            name="secteur",
            field=models.CharField(blank=True, db_index=True, max_length=100,
                                   null=True),
        ),
    ]
