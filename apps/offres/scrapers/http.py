"""Appels HTTP avec reprise sur erreur transitoire.

Les API de la Banque mondiale renvoient occasionnellement un 500 sans raison :
observe en pleine collecte, un seul hoquet suffisait a faire perdre toute la
source pour le run. Sur un rattrapage complet de plusieurs heures, c'est
inacceptable.
"""

import time

import requests

# Codes qui valent la peine d'etre retentes : panne passagere ou surcharge.
# Un 404 ou un 400 ne se corrigera pas en re-essayant.
CODES_TRANSITOIRES = {429, 500, 502, 503, 504}


def get(url: str, headers: dict, params: dict = None,
        timeout: int = 30, tentatives: int = 3):
    """GET avec repli exponentiel sur erreur transitoire. Renvoie la reponse."""
    derniere = None

    for essai in range(tentatives):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
            if resp.status_code in CODES_TRANSITOIRES and essai < tentatives - 1:
                attente = 2 ** essai
                print(f"  HTTP {resp.status_code} transitoire, "
                      f"nouvelle tentative dans {attente}s...")
                time.sleep(attente)
                continue
            resp.raise_for_status()
            return resp
        except (requests.RequestException, ValueError) as exc:
            derniere = exc
            # Une erreur definitive (400, 404, 403...) ne se corrigera pas en
            # re-essayant : on abandonne immediatement. Sans ce test, la fin
            # de pagination des API WordPress -- qui repond 400 -- coutait
            # trois secondes d'attente inutile a chaque source.
            statut = getattr(getattr(exc, "response", None), "status_code", None)
            if statut and statut not in CODES_TRANSITOIRES:
                raise
            if essai < tentatives - 1:
                attente = 2 ** essai
                print(f"  Appel echoue ({str(exc)[:60]}), "
                      f"nouvelle tentative dans {attente}s...")
                time.sleep(attente)

    raise derniere if derniere else RuntimeError(f"echec de l'appel a {url}")


def get_json(url: str, headers: dict, params: dict = None,
             timeout: int = 30, tentatives: int = 3) -> dict:
    """GET renvoyant du JSON deja decode."""
    return get(url, headers, params, timeout, tentatives).json()


def get_html(url: str, headers: dict, params: dict = None,
             timeout: int = 20, tentatives: int = 3) -> str:
    """GET renvoyant le HTML. Meme reprise que pour les API.

    unjobnet renvoie parfois un 500 en pleine pagination, probablement pour
    limiter le debit : sans reprise, une collecte de 27 pages etait perdue.
    """
    return get(url, headers, params, timeout, tentatives).text


def post_json(url: str, headers: dict, corps: dict,
              timeout: int = 40, tentatives: int = 3) -> dict:
    """POST JSON avec la meme reprise que get(). Renvoie le JSON decode.

    Necessaire pour l'API TED, qui n'accepte la recherche qu'en POST : un GET
    y repond 405.
    """
    derniere = None

    for essai in range(tentatives):
        try:
            resp = requests.post(url, headers=headers, json=corps, timeout=timeout)
            if resp.status_code in CODES_TRANSITOIRES and essai < tentatives - 1:
                attente = 2 ** essai
                print(f"  HTTP {resp.status_code} transitoire, "
                      f"nouvelle tentative dans {attente}s...")
                time.sleep(attente)
                continue
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            derniere = exc
            statut = getattr(getattr(exc, "response", None), "status_code", None)
            if statut and statut not in CODES_TRANSITOIRES:
                raise
            if essai < tentatives - 1:
                time.sleep(2 ** essai)

    raise derniere if derniere else RuntimeError(f"echec de l'appel a {url}")
