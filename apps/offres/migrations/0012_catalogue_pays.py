import unicodedata

from django.db import migrations, models
from django.utils.text import slugify


def code_pays(valeur):
    texte = (valeur or "").strip().lower()
    for signe in ("'", "’", "ʼ", "-", "_", ",", ".", "(", ")", "/"):
        texte = texte.replace(signe, " ")
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return slugify(" ".join(texte.split()), allow_unicode=False)[:100]


def remplir_catalogue(apps, schema_editor):
    alias_db = schema_editor.connection.alias
    Offre = apps.get_model("offres", "Offre")
    Pays = apps.get_model("offres", "Pays")
    noms = {}
    valeurs = (Offre.objects.using(alias_db)
               .exclude(pays__isnull=True).exclude(pays="")
               .values_list("pays", flat=True).distinct().order_by("pays"))
    for valeur in valeurs.iterator(chunk_size=500):
        code = code_pays(valeur)
        if code:
            noms.setdefault(code, valeur.strip()[:100])
    Pays.objects.using(alias_db).bulk_create(
        [Pays(code=code, nom=nom) for code, nom in noms.items()],
        ignore_conflicts=True, batch_size=500)


class Migration(migrations.Migration):

    dependencies = [("offres", "0011_fusionner_secteurs_synonymes")]

    operations = [
        migrations.CreateModel(
            name="Pays",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("code", models.SlugField(db_index=True, max_length=100, unique=True)),
                ("nom", models.CharField(max_length=100, verbose_name="nom affiché")),
                ("actif", models.BooleanField(db_index=True, default=True)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "pays",
                "verbose_name_plural": "pays",
                "db_table": "pays_catalogue",
                "ordering": ["nom", "code"],
            },
        ),
        migrations.RunPython(remplir_catalogue, migrations.RunPython.noop),
    ]
