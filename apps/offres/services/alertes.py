"""Alertes email : les nouvelles offres envoyées aux utilisateurs concernés.

Lancé à la fin de chaque traitement complet (`manage.py tout`, toutes les 6 h
par le planificateur) ou à la main (`manage.py envoyer_alertes`).

1. Les offres ajoutées depuis le dernier passage (repère `alertes_depuis`)
   sont comparées aux critères de chaque utilisateur qui accepte les alertes.
2. Chaque correspondance au-dessus de son seuil devient une Notification
   « en attente ». L'unicité (user, offre) en base interdit les doublons,
   même si deux passages se chevauchent.
3. Un email récapitulatif par utilisateur. Succès : « envoyée ». Échec :
   « échec », retenté aux passages suivants jusqu'à TENTATIVES_MAX.

Seules les adresses vérifiées reçoivent des alertes : sinon n'importe qui
pourrait faire envoyer des emails à l'adresse d'un autre.
"""

from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.offres.models import Notification, Parametres
from apps.offres.services.correspondance import criteres, ouvertes, score
from apps.offres.services.notification import NotificationService

#: Premier passage : on remonte d'une journée, pas sur toute la base.
PREMIER_PASSAGE = timedelta(hours=24)


def destinataires():
    """Comptes actifs, alertes acceptées, adresse principale vérifiée."""
    return (get_user_model().objects.filter(
        is_active=True, preferences__notifications=True,
        emailaddress__primary=True, emailaddress__verified=True).distinct())


def preparer(maintenant=None) -> int:
    """Crée les notifications en attente. Renvoie le nombre de créations."""
    maintenant = maintenant or timezone.now()
    with transaction.atomic():
        reglages = Parametres.objects.select_for_update().get(pk=Parametres.charger().pk)
        depuis = reglages.alertes_depuis or maintenant - PREMIER_PASSAGE
        nouvelles = ouvertes().filter(date_ajout__gt=depuis, date_ajout__lte=maintenant)
        if settings.API_PUBLIQUE_SOURCES_EXCLUES:
            # Sources qui interdisent la rediffusion : elles ne sortent pas par email.
            nouvelles = nouvelles.exclude(source__in=settings.API_PUBLIQUE_SOURCES_EXCLUES)
        nouvelles = list(nouvelles)
        poids = reglages.ponderation()
        a_creer = []
        for user in destinataires() if nouvelles else []:
            c = criteres(user)
            for offre in nouvelles:
                if c.types and offre.nature not in c.types:
                    continue
                s = score(offre, c, poids)
                if s >= c.seuil and not c.vide:
                    a_creer.append(Notification(user=user, offre=offre, score=s))
        Notification.objects.bulk_create(a_creer, ignore_conflicts=True)
        reglages.alertes_depuis = maintenant
        reglages.save(update_fields=["alertes_depuis"])
    return len(a_creer)


def corps(user, notifications) -> str:
    lignes = [f"Bonjour {user.first_name or ''},".replace(" ,", ","), "",
              f"{len(notifications)} nouvelle(s) offre(s) correspondent à votre profil :", ""]
    for n in notifications:
        o = n.offre
        echeance = o.date_limite.strftime("%d/%m/%Y") if o.date_limite else "non précisée"
        lien = f"{settings.SITE_URL}/offre/{o.pk}/" if settings.SITE_URL else (o.lien or "")
        lignes += [f"[{n.score} %] {o.titre}",
                   f"{o.organisation or '-'} — {o.pays or '-'} — clôture : {echeance}", lien, ""]
    reglage = f"{settings.SITE_URL}/profil/#preferences" if settings.SITE_URL else "votre profil"
    lignes.append(f"Préférences et désinscription des alertes : {reglage}")
    return "\n".join(lignes)


def envoyer() -> dict:
    """Envoie les notifications en attente (et les échecs à retenter)."""
    a_envoyer = (Notification.objects
                 .filter(Q(statut=Notification.EN_ATTENTE)
                         | Q(statut=Notification.ECHEC, tentatives__lt=Notification.TENTATIVES_MAX))
                 .filter(user__in=destinataires())
                 .select_related("user", "offre").order_by("-score"))
    par_user = defaultdict(list)
    for n in a_envoyer:
        par_user[n.user].append(n)

    bilan = {"emails": 0, "offres": 0, "echecs": 0}
    for user, notifications in par_user.items():
        ids = [n.pk for n in notifications]
        try:
            NotificationService.envoyer_a(
                [user.email], f"{len(notifications)} nouvelle(s) offre(s) pour vous",
                corps(user, notifications))
        except Exception as exc:
            Notification.objects.filter(pk__in=ids).update(
                statut=Notification.ECHEC, tentatives=F("tentatives") + 1, erreur=str(exc)[:500])
            bilan["echecs"] += 1
            continue
        Notification.objects.filter(pk__in=ids).update(
            statut=Notification.ENVOYEE, envoye_le=timezone.now(),
            tentatives=F("tentatives") + 1, erreur="")
        bilan["emails"] += 1
        bilan["offres"] += len(ids)
    return bilan


def traiter() -> dict:
    return {"creees": preparer(), **envoyer()}
