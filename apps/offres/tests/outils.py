"""Adaptateur : les anciens tests de scrapers sont des fonctions test_*.

en_cas_de_test(globals()) en fait un SimpleTestCase que le lanceur Django
decouvre, sans reecrire chaque assertion.
"""

from django.test import SimpleTestCase


def en_cas_de_test(espace: dict, nom: str = "Essais"):
    attributs = {cle: staticmethod(f) for cle, f in espace.items()
                 if cle.startswith("test_") and callable(f)}
    return type(nom, (SimpleTestCase,), attributs)
