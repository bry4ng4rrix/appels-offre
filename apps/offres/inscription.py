"""Anti-multicomptes et essai gratuit, branchés sur allauth.

- Un appareil (cookie `lc_appareil` posé par le frontend) ne crée qu'un compte : l'inscription
  suivante est refusée (`FormulaireInscription`, ACCOUNT_SIGNUP_FORM_CLASS).
- Une IP déjà vue crée un compte, mais sans essai gratuit : beaucoup d'utilisateurs partagent
  une IP (opérateurs mobiles, bureaux, cybercafés).

Ce module est importé par allauth.account.forms : rien d'allauth au niveau du module.
"""

import hashlib
import hmac
import ipaddress
from datetime import timedelta

from django import forms
from django.conf import settings
from django.utils import timezone

MESSAGE_APPAREIL = "Un compte a déjà été créé depuis cet appareil. Connectez-vous avec ce compte."


def empreinte(valeur: str) -> str:
    """HMAC de l'IP ou de l'appareil : comparable, mais illisible si la base fuit."""
    if not valeur:
        return ""
    return hmac.new(settings.SECRET_KEY.encode(), valeur.encode(), hashlib.sha256).hexdigest()


def origine(requete) -> tuple[str, str]:
    """(IP, identifiant d'appareil) du visiteur, en clair.

    Le frontend Next appelle Django depuis une adresse privée (réseau Docker, ou localhost en
    développement) et transmet l'IP et l'appareil du visiteur en en-têtes. Un appel direct depuis
    Internet n'est cru que pour son adresse réelle : ses en-têtes sont ignorés.
    shortcut: Django derrière un proxy inverse sur le même réseau verrait tout le monde en privé ;
    dans ce cas, faire écrire X-Client-Ip par ce proxy.
    """
    ip = requete.META.get("REMOTE_ADDR", "")
    try:
        interne = ipaddress.ip_address(ip).is_private
    except ValueError:
        interne = False
    if not interne:
        return ip, ""
    return requete.headers.get("X-Client-Ip", "").strip() or ip, requete.headers.get("X-Appareil", "").strip()


class FormulaireInscription(forms.Form):
    """Base du formulaire d'inscription d'allauth (pages web et API headless)."""

    def clean(self):
        from allauth.core import context

        from .models import Inscription

        donnees = super().clean()
        _, appareil = origine(context.request)
        if appareil and Inscription.objects.filter(appareil=empreinte(appareil)).exists():
            raise forms.ValidationError(MESSAGE_APPAREIL, code="appareil_deja_utilise")
        return donnees

    def signup(self, request, user):
        """Rien ici : `enregistrer` (signal) couvre aussi les inscriptions sociales."""


def enregistrer(request, user, **_):
    """Signal user_signed_up : empreintes, et essai gratuit si l'IP est nouvelle."""
    from .models import Inscription

    ip, appareil = (empreinte(v) for v in origine(request))
    deja_vue = bool(ip) and Inscription.objects.filter(ip=ip).exists()
    fin = None if deja_vue else timezone.localdate() + timedelta(days=Inscription.ESSAI_JOURS - 1)
    Inscription.objects.update_or_create(user=user, defaults={"ip": ip, "appareil": appareil,
                                                              "essai_jusqu_au": fin})
