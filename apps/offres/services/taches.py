"""Avancement des taches de fond, ecrit en base pour l'interface web."""

import socket
import subprocess
import sys
from contextlib import contextmanager

from django.conf import settings
from django.utils import timezone

from apps.offres.models import Tache


class DejaEnCours(Exception):
    def __init__(self, tache):
        super().__init__(f"{tache.libelle} est deja en cours")
        self.tache = tache


def demarrer(nom: str, automatique: bool = False):
    """Lance `manage.py <commande> --tache <id>` en arriere-plan, sortie dans
    logs/tache-<id>.log. Une seule tache a la fois. Rend (tache, processus)."""
    en_cours = Tache.active()
    if en_cours:
        raise DejaEnCours(en_cours)
    commande = Tache.TYPES[nom][0]
    tache = Tache.objects.create(nom=nom, hote=socket.gethostname(), etape="Démarrage…",
                                 automatique=automatique)
    tache.chemin_journal.parent.mkdir(exist_ok=True)
    try:
        with open(tache.chemin_journal, "w") as journal:
            # -u : sortie non bufferisee, sinon le journal reste vide jusqu'a la fin.
            processus = subprocess.Popen(
                [sys.executable, "-u", str(settings.BASE_DIR / "manage.py"), commande,
                 "--tache", str(tache.pk)],
                cwd=settings.BASE_DIR, stdout=journal, stderr=subprocess.STDOUT,
                start_new_session=True)
    except OSError as exc:
        Tache.objects.filter(pk=tache.pk).update(statut=Tache.ECHEC, fin=timezone.now(),
                                                 detail=f"Lancement impossible : {exc}")
        raise
    Tache.objects.filter(pk=tache.pk).update(pid=processus.pid)
    tache.refresh_from_db()
    return tache, processus


def sans_suivi(**_):
    """Progression par defaut : la ligne de commande se contente de rich."""


class Progression:
    """Appelable : progression(etape=..., courant=..., total=..., detail=...).

    Sans tache (lancement en ligne de commande), ne fait rien.
    """

    def __init__(self, tache_id=None):
        self.tache_id = tache_id

    def __call__(self, **champs):
        if self.tache_id:
            champs = {k: v for k, v in champs.items() if v is not None}
            Tache.objects.filter(pk=self.tache_id).update(maj_le=timezone.now(), **champs)

    def phase(self, numero: int):
        self(phase=numero, courant=0, total=0, detail="")

    def finir(self, statut, detail=None):
        self(statut=statut, fin=timezone.now(), detail=detail)


@contextmanager
def suivre(tache_id):
    """Entoure une commande : la tache est close, en succes ou en echec."""
    progression = Progression(tache_id)
    try:
        yield progression
    except BaseException as exc:  # KeyboardInterrupt compris
        progression.finir(Tache.ECHEC, f"Échec : {exc}"[:500] or type(exc).__name__)
        raise
    else:
        progression.finir(Tache.TERMINEE)
