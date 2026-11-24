"""Comptes utilisateurs : roles et adaptation d'allauth.

Deux roles, sans modele dedie : ADMIN = `is_staff` (deja celui de /admin/),
USER = tout autre compte actif. Le premier admin se cree avec
`manage.py creer_admin` ; aucune page ne permet de s'inscrire admin.
"""

from functools import wraps

from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import PermissionDenied


def est_admin(user) -> bool:
    return user.is_authenticated and user.is_active and user.is_staff


def admin_requis(vue):
    """Reserve une vue aux admins. La connexion est deja exigee par
    LoginRequiredMiddleware ; un USER connecte recoit un 403, pas une page de connexion."""
    @wraps(vue)
    def garde(requete, *args, **kwargs):
        if not est_admin(requete.user):
            raise PermissionDenied("Réservé aux administrateurs.")
        return vue(requete, *args, **kwargs)
    return garde


class CompteAdapter(DefaultAccountAdapter):

    def get_login_redirect_url(self, requete):
        # Un admin arrive sur la liste complete, un utilisateur sur ses suggestions.
        return reverse("web-liste") if est_admin(requete.user) else reverse("web-pour-vous")

    def send_mail(self, template_prefix, email, ctx):
        """Verification et reinitialisation partent par le meme serveur que le
        recapitulatif : l'onglet Email prime sur le .env."""
        from apps.offres.services.notification import NotificationService

        requete = context.request
        msg = self.render_mail(template_prefix, email, {
            "request": requete, "email": email,
            "current_site": get_current_site(requete), **ctx})
        mailer, expediteur, _ = NotificationService.configuration()
        msg.from_email = expediteur
        mailer.send_messages([msg])
