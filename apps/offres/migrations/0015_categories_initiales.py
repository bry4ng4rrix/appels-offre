"""Catégories de recherche de départ, tirées du cahier des charges.

Informatique et Finance n'y sont pas : ce sont déjà des secteurs (catalogue Secteur).
L'admin les complète ensuite dans /admin/.
"""

from django.db import migrations

CATEGORIES = [
    ("developpement-web", "Développement web"), ("backend", "Backend"),
    ("developpement-mobile", "Développement mobile"),
    ("intelligence-artificielle", "Intelligence artificielle"),
    ("data-science", "Data Science"), ("cybersecurite", "Cybersécurité"),
    ("marketing", "Marketing"), ("administration", "Administration"),
    ("design", "Design"), ("commerce", "Commerce"),
    ("ressources-humaines", "Ressources humaines"),
]


def creer(apps, schema_editor):
    Categorie = apps.get_model("offres", "Categorie")
    for code, nom in CATEGORIES:
        Categorie.objects.get_or_create(code=code, defaults={"nom": nom})


class Migration(migrations.Migration):
    dependencies = [("offres", "0014_profils_et_alertes")]
    operations = [migrations.RunPython(creer, migrations.RunPython.noop)]
