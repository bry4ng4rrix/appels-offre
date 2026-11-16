from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("offres", "0008_secteur_libre")]

    operations = [
        migrations.AddField(
            model_name="parametres",
            name="intervalle_collecte",
            field=models.PositiveSmallIntegerField(default=6,
                                                    verbose_name="intervalle de collecte en heures"),
        ),
    ]
