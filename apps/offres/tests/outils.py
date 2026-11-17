"""Adaptateur : les anciens tests de scrapers sont des fonctions test_*.

en_cas_de_test(globals()) en fait un SimpleTestCase que le lanceur Django
decouvre, sans reecrire chaque assertion.
"""

from django.test import SimpleTestCase, TestCase


def en_cas_de_test(espace: dict, nom: str = "Essais"):
    attributs = {"__module__": espace["__name__"]}
    attributs.update({cle: staticmethod(f) for cle, f in espace.items()
                      if cle.startswith("test_") and callable(f)})
    return type(nom, (SimpleTestCase,), attributs)


def connecter(client, admin: bool = True):
    """Ouvre une session : ADMIN (is_staff) par defaut, USER sinon."""
    from django.contrib.auth import get_user_model
    nom = "admin-test" if admin else "membre-test"
    user = get_user_model().objects.create_user(
        nom, email=f"{nom}@exemple.org", password="mdp-de-test-1234", is_staff=admin)
    client.force_login(user)
    return user


class AvecAdmin(TestCase):
    """Les vues d'administration (taches, parametres) exigent un admin connecte."""

    def setUp(self):
        super().setUp()
        self.admin = connecter(self.client)
