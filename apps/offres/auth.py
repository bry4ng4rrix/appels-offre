"""Protection des endpoints /api/ par jeton.

Le decorateur `token_requis` s'applique aux vues JSON. L'admin, lui, reste
sous l'authentification de session de Django : il a deja sa page de connexion.

Trois choix a expliciter.

1. Le jeton se presente dans un EN-TETE, jamais dans l'URL. Un jeton en
   query string se retrouve dans les journaux du serveur, dans l'historique
   du navigateur et dans l'en-tete Referer envoye aux sites tiers. Deux
   formes sont acceptees :

       Authorization: Bearer veille_xxx
       X-API-Key: veille_xxx

2. La verification tient meme si la base n'a aucune cle : l'API est alors
   fermee, et le message 401 dit comment en creer une. Une API qui s'ouvrirait
   faute de cle serait le contraire de ce qu'on veut.

3. La protection s'applique aussi en local et en DEBUG. C'est la demande
   explicite : une machine de developpement heberge d'autres processus, et
   127.0.0.1 n'est pas une frontiere de securite.
"""

import hashlib
import secrets
from datetime import timedelta
from functools import wraps

from django.http import JsonResponse
from django.utils import timezone

#: Longueur en octets de l'alea. 32 octets = 256 bits, soit 43 caracteres
#: une fois encodes en URL-safe base64.
OCTETS_ALEA = 32

#: La date de derniere utilisation n'est ecrite que si elle a vieilli
#: d'autant : sans ce garde-fou, chaque GET declencherait un UPDATE.
FRAICHEUR_USAGE = timedelta(minutes=15)


def empreinte(jeton: str) -> str:
    """Empreinte SHA-256 d'un jeton, en hexadecimal."""
    return hashlib.sha256((jeton or "").encode("utf-8")).hexdigest()


def engendrer() -> str:
    """Un nouveau jeton, prefixe pour etre reconnaissable."""
    from .models import CleApi
    return CleApi.PREFIXE + secrets.token_urlsafe(OCTETS_ALEA)


def jeton_presente(requete) -> str:
    """Jeton lu dans les en-tetes, chaine vide s'il n'y en a pas."""
    brut = requete.headers.get("Authorization", "")
    if brut.lower().startswith("bearer "):
        return brut[7:].strip()
    return (requete.headers.get("X-API-Key") or "").strip()


def cle_valide(jeton: str):
    """Renvoie la CleApi active correspondante, ou None.

    La recherche porte sur l'empreinte, pas sur le jeton : la base n'en
    contient aucun. `compare_digest` protege la comparaison finale d'une
    attaque temporelle -- la recherche par index, elle, ne revele rien
    d'exploitable puisqu'elle porte deja sur un condense.
    """
    from .models import CleApi

    if not jeton:
        return None

    attendue = empreinte(jeton)
    cle = CleApi.objects.filter(empreinte=attendue, revoque_le__isnull=True).first()
    if cle is None:
        return None
    if not secrets.compare_digest(cle.empreinte, attendue):
        return None
    return cle


def marquer_usage(cle) -> None:
    """Note la derniere utilisation, sans ecrire a chaque appel."""
    maintenant = timezone.now()
    if (cle.derniere_utilisation is None
            or maintenant - cle.derniere_utilisation > FRAICHEUR_USAGE):
        cle.derniere_utilisation = maintenant
        cle.save(update_fields=["derniere_utilisation"])


def refus(message: str) -> JsonResponse:
    """401 en JSON : l'appelant attend du JSON, pas une page d'erreur HTML."""
    reponse = JsonResponse({"erreur": message}, status=401,
                           json_dumps_params={"ensure_ascii": False})
    # Sans cet en-tete, un client HTTP conforme ne sait pas quoi presenter.
    reponse["WWW-Authenticate"] = 'Bearer realm="veille"'
    return reponse


def token_requis(vue):
    """Exige un jeton valide. A appliquer a toute vue sous /api/."""

    @wraps(vue)
    def enveloppe(requete, *args, **kwargs):
        from .models import CleApi

        jeton = jeton_presente(requete)
        if not jeton:
            return refus("Jeton absent. Presentez un en-tete "
                         "'Authorization: Bearer <jeton>' ou 'X-API-Key'.")

        cle = cle_valide(jeton)
        if cle is None:
            # Le message ne distingue pas jeton inconnu, revoque ou mal
            # recopie : cela renseignerait un attaquant sans aider personne.
            if not CleApi.objects.filter(revoque_le__isnull=True).exists():
                return refus("Jeton invalide, et aucune cle active n'existe. "
                             "Creez-en une : manage.py cle_api --creer <nom>")
            return refus("Jeton invalide ou revoque.")

        marquer_usage(cle)
        requete.cle_api = cle
        return vue(requete, *args, **kwargs)

    return enveloppe
