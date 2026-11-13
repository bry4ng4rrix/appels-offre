"""Avancement des taches de fond, ecrit en base pour l'interface web."""

import socket
import subprocess
import sys
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from apps.offres.models import Tache, debut_processus


def prochaine_execution(maintenant: datetime, heure) -> datetime:
    """Prochaine occurrence de `heure` apres `maintenant` (datetime locale)."""
    cible = maintenant.replace(hour=heure.hour, minute=heure.minute, second=0, microsecond=0)
    return cible if cible > maintenant else cible + timedelta(days=1)


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
    # Un nouveau lancement rend caduque une tache du meme type en attente de reprise.
    Tache.objects.filter(nom=nom, statut=Tache.INTERROMPUE).update(
        statut=Tache.ECHEC, fin=timezone.now(), detail="Remplacée par un nouveau lancement.")
    tache = Tache.objects.create(nom=nom, hote=socket.gethostname(), etape="Démarrage…",
                                 automatique=automatique)
    return _lancer(tache, mode="w")


def reprendre(tache):
    """Relance une tache interrompue, sur la meme ligne et le meme journal.
    La commande lit `tache.reprise` et saute ce qui est deja fait."""
    en_cours = Tache.active()
    if en_cours:
        raise DejaEnCours(en_cours)
    if tache.reprises >= Tache.REPRISES_MAX:
        Tache.objects.filter(pk=tache.pk).update(
            statut=Tache.ECHEC, fin=timezone.now(),
            detail=f"Abandonnée après {tache.reprises} reprises : elle retombe à chaque fois.")
        return None
    Tache.objects.filter(pk=tache.pk).update(
        statut=Tache.EN_COURS, reprises=tache.reprises + 1, hote=socket.gethostname(),
        fin=None, etape="Reprise…", maj_le=timezone.now())
    tache.refresh_from_db()
    return _lancer(tache, mode="a")


def _lancer(tache, mode: str):
    commande = Tache.TYPES[tache.nom][0]
    tache.chemin_journal.parent.mkdir(exist_ok=True)
    try:
        with open(tache.chemin_journal, mode) as journal:
            if tache.reprises:
                journal.write(f"\n===== Reprise n°{tache.reprises} — {timezone.localtime():%d/%m/%Y %H:%M} "
                              "(ce qui est déjà fait est sauté) =====\n")
                journal.flush()
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
    Tache.objects.filter(pk=tache.pk).update(pid=processus.pid,
                                             pid_debut=debut_processus(processus.pid))
    tache.refresh_from_db()
    return tache, processus


class Progression:
    """Appelable : progression(etape=..., courant=..., total=..., detail=...).

    Porte aussi l'etat de reprise de la tache (`etat`, `sauver`, `phase_atteinte`).
    Sans tache (lancement en ligne de commande), n'ecrit rien.
    """

    def __init__(self, tache_id=None):
        self.tache_id = tache_id
        self.etat, self.debut, self.phase_atteinte = {}, None, 1
        if tache_id:
            ligne = Tache.objects.filter(pk=tache_id).values("reprise", "debut", "phase").first()
            if ligne:
                self.etat = dict(ligne["reprise"] or {})
                self.debut, self.phase_atteinte = ligne["debut"], ligne["phase"]

    def __call__(self, **champs):
        if self.tache_id:
            champs = {k: v for k, v in champs.items() if v is not None}
            Tache.objects.filter(pk=self.tache_id).update(maj_le=timezone.now(), **champs)

    def sauver(self, **valeurs):
        """Point de reprise : ce qui est fait ne sera pas refait apres une coupure."""
        self.etat.update(valeurs)
        self(reprise=self.etat)

    def phase(self, numero: int):
        self(phase=numero, courant=0, total=0, detail="")

    def finir(self, statut, detail=None):
        self(statut=statut, fin=timezone.now(), detail=detail)


#: Intervalle du battement de coeur d'une tache en cours (voir Tache.SILENCE_MAX).
BATTEMENT = 30


def _battre(tache_id, arret):
    """Tant que la commande tourne, signale qu'elle est vivante, meme pendant
    une longue page (Crawl-delay de 10 s a la BAD) qui ne donne aucune progression."""
    from django.db import connection
    try:
        while not arret.wait(BATTEMENT):
            Tache.objects.filter(pk=tache_id, statut=Tache.EN_COURS).update(maj_le=timezone.now())
    finally:
        connection.close()


@contextmanager
def suivre(tache_id):
    """Entoure une commande : la tache est close, en succes ou en echec.

    Un processus tue (conteneur ou VPS redemarre) n'arrive jamais ici : la tache
    reste "en cours", son battement s'arrete, et Tache.active() la fait passer
    "interrompue" pour que le planificateur la reprenne.
    """
    progression = Progression(tache_id)
    arret = threading.Event()
    battement = threading.Thread(target=_battre, args=(tache_id, arret), daemon=True)
    if tache_id:
        battement.start()
    try:
        yield progression
    except BaseException as exc:  # KeyboardInterrupt compris : un arret voulu n'est pas repris
        progression.finir(Tache.ECHEC, f"Échec : {exc}"[:500] or type(exc).__name__)
        raise
    else:
        progression.finir(Tache.TERMINEE)
    finally:
        arret.set()
        if battement.is_alive():
            battement.join(timeout=5)
