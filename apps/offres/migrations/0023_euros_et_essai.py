"""Prix des plans en euros (1 € = 5 000 Ar), et essai gratuit de 14 jours.
Les comptes existants ont leurs 14 jours à partir de cette migration (la mise en ligne)."""

from datetime import timedelta
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone

ARIARY_PAR_EURO = Decimal(5000)


def en_euros(apps, schema_editor):
    for plan in apps.get_model("offres", "Plan").objects.all():
        plan.prix = (Decimal(plan.prix) / ARIARY_PAR_EURO).quantize(Decimal("0.01"))
        plan.save(update_fields=["prix"])


def en_ariary(apps, schema_editor):
    for plan in apps.get_model("offres", "Plan").objects.all():
        plan.prix = (Decimal(plan.prix) * ARIARY_PAR_EURO).quantize(Decimal(1))
        plan.save(update_fields=["prix"])


def essai_des_comptes_existants(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    Inscription = apps.get_model("offres", "Inscription")
    fin = timezone.localdate() + timedelta(days=13)  # 14 jours, aujourd'hui compris
    Inscription.objects.bulk_create(Inscription(user=u, essai_jusqu_au=fin) for u in User.objects.all())


class Migration(migrations.Migration):

    dependencies = [
        ('offres', '0022_plans_initiaux'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='plan',
            name='par_jour',
            field=models.BooleanField(default=False, help_text='Coché : les crédits sont disponibles chaque jour de la période. Décoché : un lot unique, utilisé une fois les crédits du jour épuisés.', verbose_name='crédits chaque jour'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='prix',
            field=models.DecimalField(decimal_places=2, max_digits=8, validators=[django.core.validators.MinValueValidator(0)], verbose_name='prix (€)'),
        ),
        migrations.CreateModel(
            name='Inscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('essai_jusqu_au', models.DateField(blank=True, help_text="Dernier jour inclus ; vide = pas d'essai.", null=True, verbose_name="essai gratuit jusqu'au")),
                ('ip', models.CharField(blank=True, db_index=True, max_length=64, verbose_name="empreinte de l'IP")),
                ('appareil', models.CharField(blank=True, db_index=True, max_length=64, verbose_name="empreinte de l'appareil")),
                ('cree_le', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='inscription', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'inscriptions',
            },
        ),
        migrations.RunPython(en_euros, en_ariary),
        migrations.RunPython(essai_des_comptes_existants, migrations.RunPython.noop),
    ]
