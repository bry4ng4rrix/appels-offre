"""Travaux independants en parallele, resultats rendus au fil appelant.

Sert a la collecte et a la verification des liens : chaque groupe (une source,
ou des sources partageant un domaine) tourne dans son propre fil et garde ses
delais de politesse ; plusieurs groupes avancent en meme temps. Les ecritures
en base se font dans le fil appelant, au fil des resultats : une seule
connexion, aucun verrou, des points de reprise toujours coherents.
"""

import queue
import threading
from concurrent.futures import ThreadPoolExecutor

_FIN = object()


def en_parallele(groupes: dict, travail, max_fils: int):
    """Lance travail(cle, elements, emettre) pour chaque groupe, `max_fils` a la fois.

    Rend les (cle, evenement) que les travaux passent a `emettre`, dans le fil
    appelant et au fur et a mesure. Une exception levee par un travail remonte ici.
    """
    file = queue.Queue()

    def executer(cle, elements):
        threading.current_thread().name = str(cle)  # prefixe des traces HTTP
        try:
            travail(cle, elements, lambda evenement: file.put((cle, evenement)))
        except BaseException as exc:
            file.put((cle, exc))
        finally:
            file.put((cle, _FIN))

    pool = ThreadPoolExecutor(max_workers=max(1, max_fils))
    try:
        for cle, elements in groupes.items():
            pool.submit(executer, cle, elements)
        restants = len(groupes)
        while restants:
            cle, evenement = file.get()
            if evenement is _FIN:
                restants -= 1
            elif isinstance(evenement, BaseException):
                raise evenement
            else:
                yield cle, evenement
    finally:
        # Interruption : ne pas attendre les groupes encore en cours.
        pool.shutdown(wait=False, cancel_futures=True)
