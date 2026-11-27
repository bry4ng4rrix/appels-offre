"""Operations d'administration partagees par l'interface web (views_web, HTMX)
et l'API applicative (views_app, JSON).

Chaque fonction valide la saisie, applique le changement et renvoie le message
a afficher. Une saisie refusee leve ValueError, dont le texte est le message
d'erreur : chaque interface le presente a sa facon (toast, JSON), mais la
regle n'est ecrite qu'ici.
"""

import re
from datetime import date, datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .auth import empreinte, engendrer
from .models import CleApi, Offre, Parametres, Pays, Secteur, Suivi, Tache
from .services.notification import NotificationService
from .services.taches import DejaEnCours, demarrer, reprendre
from .services.taxonomie import code_pays, code_secteur

CRITERES_SCORE = [("competences", "Compétences"), ("domaine", "Domaine (secteur)"),
                  ("categorie", "Catégorie"), ("localisation", "Localisation"),
                  ("mots_cles", "Mots-clés")]


def _texte(donnees, cle: str) -> str:
    return str(donnees.get(cle) or "").strip()


# ----------------------------------------------------------------- offres

#: Une note est un motif ou une consigne, pas un dossier ; au-dela, c'est
#: presque surement un corps mal adresse.
NOTE_MAX = 2000


def decider_offre(offre, donnees, user=None, cle=None) -> tuple:
    """Pose ou change le statut commercial : {"statut", "note" facultative}.
    Une note absente laisse la note en place ; une note vide l'efface.
    L'auteur est l'admin connecte (user) ou la cle d'API (cle). Renvoie (suivi, cree)."""
    statut = donnees.get("statut")
    if statut not in dict(Suivi.STATUT_CHOICES):
        raise ValueError(f"Statut inconnu. Attendu : {', '.join(dict(Suivi.STATUT_CHOICES))}.")
    champs = {"statut": statut, "decide_par": user, "decide_par_cle": cle}
    if "note" in donnees:
        note = donnees.get("note")
        if note is not None and not isinstance(note, str):
            raise ValueError("La note doit etre une chaine.")
        note = (note or "").strip()
        if len(note) > NOTE_MAX:
            raise ValueError(f"Note trop longue ({len(note)} caracteres, maximum {NOTE_MAX}).")
        champs["note"] = note
    return Suivi.objects.update_or_create(offre_id=offre.pk, defaults=champs)


def dater_offre(offre, brut, user=None, cle=None) -> tuple:
    """Saisit l'echeance qu'une source ne publie pas. Ecrite a deux endroits, comme
    a l'ecran : suivi.echeance, trace de la decision qui survit a tout re-tri, et
    offres.date_limite, ce que lisent toutes les vues sans jointure. Renvoie (date, suivi)."""
    if isinstance(brut, date):
        valeur = brut
    elif isinstance(brut, str):
        try:
            valeur = date.fromisoformat(brut.strip())
        except ValueError:
            raise ValueError("Date illisible : attendu AAAA-MM-JJ.")
    else:
        raise ValueError("Champ 'echeance' attendu, au format AAAA-MM-JJ.")
    maintenant = timezone.now()
    with transaction.atomic():
        suivi, _ = Suivi.objects.update_or_create(
            offre_id=offre.pk,
            defaults={"echeance": valeur, "echeance_saisie_le": maintenant,
                      "decide_par": user, "decide_par_cle": cle})
        Offre.objects.filter(pk=offre.pk).update(date_limite=valeur, date_maj=maintenant)
    return valeur, suivi


def juger_offre(offre, pertinent) -> bool:
    """Corrige le verdict du tri. Un re-tri peut le rendre : pour ecarter
    durablement, poser le statut "hors_sujet", qui lui survit."""
    if not isinstance(pertinent, bool):
        raise ValueError("Champ 'pertinent' attendu : true ou false.")
    Offre.objects.filter(pk=offre.pk).update(pertinent=pertinent, date_maj=timezone.now())
    return pertinent


# ------------------------------------------------------------ parametres

def regler_collecte(reglages, intervalle, heure_nuit="", pause_weekend=None) -> str:
    """Frequence de la collecte automatique (1 a 24 h), heure de la nuit (HH:MM),
    pause du week-end (None : inchangee)."""
    try:
        intervalle = int(intervalle)
        if not 1 <= intervalle <= 24:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Intervalle invalide : choisissez une valeur de 1 à 24 heures.")
    reglages.intervalle_collecte = intervalle
    champs = ["intervalle_collecte"]
    message = f"Collecte automatique réglée toutes les {intervalle} heure(s)."
    if heure_nuit:
        try:
            reglages.heure_nuit = datetime.strptime(heure_nuit, "%H:%M").time()
        except (TypeError, ValueError):
            raise ValueError("Heure de nuit invalide : attendu HH:MM.")
        champs.append("heure_nuit")
        message += f" Organisation de nuit à {reglages.heure_nuit:%H:%M}."
    if pause_weekend is not None:
        reglages.pause_weekend = pause_weekend
        champs.append("pause_weekend")
        message += " Pas d'automatismes le week-end." if pause_weekend else " Automatismes aussi le week-end."
    reglages.save(update_fields=champs)
    return message


def source_email(reglages) -> str:
    """D'ou vient le serveur d'envoi : saisi a l'ecran, .env, ou aucun (console)."""
    if reglages.smtp_hote:
        return "ecran"
    return "env" if settings.SMTP_HOST else "console"


def regler_email(reglages, donnees) -> tuple[str, bool]:
    """Serveur SMTP et destinataires du recapitulatif. Renvoie (message, mot de passe efface).

    Le mot de passe n'est jamais renvoye : vide = inchange. Il est efface si le
    serveur ou l'utilisateur change sans etre ressaisi, pour qu'il ne parte pas
    vers un autre serveur que celui pour lequel il a ete donne.
    """
    hote = _texte(donnees, "smtp_hote")
    utilisateur = _texte(donnees, "smtp_utilisateur")
    mot_de_passe = str(donnees.get("smtp_mot_de_passe") or "")
    securite = donnees.get("smtp_securite") or "tls"
    destinataires = [a for a in re.split(r"[,;\s]+", str(donnees.get("destinataires") or "")) if a]

    erreurs = []
    if securite not in dict(Parametres.SECURITES_SMTP):
        erreurs.append("sécurité inconnue")
    if re.search(r"[\s/]", hote) or len(hote) > 255:
        erreurs.append("serveur illisible (ex. smtp.gmail.com)")
    try:
        port = int(donnees.get("smtp_port") or {"ssl": 465, "aucune": 25}.get(securite, 587))
        if not 1 <= port <= 65535:
            raise ValueError
    except (TypeError, ValueError):
        erreurs.append("port invalide (1 à 65535)")
    invalides = []
    for adresse in destinataires:
        try:
            validate_email(adresse)
        except ValidationError:
            invalides.append(adresse)
    if invalides:
        erreurs.append("adresse invalide : " + ", ".join(invalides))
    if erreurs:
        raise ValueError("Email non enregistré : " + " ; ".join(erreurs) + ".")

    efface = False
    if not hote:
        # Serveur vide : retour au .env, rien d'inutile ne reste en base.
        utilisateur, mot_de_passe = "", ""
        reglages.smtp_mot_de_passe = ""
    elif mot_de_passe:
        reglages.smtp_mot_de_passe = mot_de_passe
    elif (hote, utilisateur) != (reglages.smtp_hote, reglages.smtp_utilisateur):
        efface = bool(reglages.smtp_mot_de_passe)
        reglages.smtp_mot_de_passe = ""
    reglages.smtp_hote, reglages.smtp_port, reglages.smtp_securite = hote, port, securite
    reglages.smtp_utilisateur = utilisateur
    reglages.destinataires = ", ".join(destinataires)
    reglages.save(update_fields=["smtp_hote", "smtp_port", "smtp_securite", "smtp_utilisateur",
                                 "smtp_mot_de_passe", "destinataires"])

    message = "Configuration email enregistrée."
    if efface:
        message += " Le serveur ou l'utilisateur a changé : saisissez à nouveau le mot de passe."
    return message, efface


def tester_email() -> tuple[str, str]:
    """Envoie un email de test avec la configuration enregistree. Renvoie (message, niveau)."""
    try:
        destinataires = NotificationService.envoyer(
            "Veille appels d'offres : email de test",
            "Cet email confirme que l'envoi du récapitulatif fonctionne.")
    except Exception as exc:
        raise ValueError(f"Échec de l'envoi : {exc}")
    if not destinataires:
        raise ValueError("Aucun destinataire : ajoutez-en au moins un.")
    if source_email(Parametres.charger()) == "console":
        return ("Aucun serveur SMTP : l'email de test est seulement écrit dans le journal du serveur.",
                "info")
    return f"Email de test envoyé à {', '.join(destinataires)}.", "succes"


def regler_poids(reglages, donnees) -> str:
    """Ponderation du score de correspondance offre / profil."""
    try:
        poids = {code: int(donnees.get(code, "")) for code, _ in CRITERES_SCORE}
        if not all(0 <= v <= 100 for v in poids.values()) or not sum(poids.values()):
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Poids invalides : des entiers de 0 à 100, pas tous nuls.")
    reglages.poids = poids
    reglages.save(update_fields=["poids"])
    return "Pondération enregistrée."


# ------------------------------------------------------ secteurs et pays

def _nom(nom) -> str:
    return str(nom or "").strip()[:100]


def creer_secteur(nom) -> str:
    nom = _nom(nom)
    code = code_secteur(nom)[:100].rstrip("_")
    if not nom or not code or code == "autre":
        raise ValueError("Nom de secteur invalide. Choisissez un nom descriptif.")
    secteur, cree = Secteur.objects.get_or_create(code=code, defaults={"nom": nom, "actif": True})
    if not cree and secteur.actif:
        raise ValueError(f"Le secteur « {secteur.nom} » existe déjà.")
    if not cree:
        secteur.nom = nom
        secteur.actif = True
        secteur.save(update_fields=["nom", "actif"])
    return f"Secteur « {nom} » ajouté au catalogue."


def renommer_secteur(secteur, nom) -> str:
    nom = _nom(nom)
    if not nom:
        raise ValueError("Le nom du secteur ne peut pas être vide.")
    secteur.nom = nom
    secteur.save(update_fields=["nom"])
    # Met aussi à jour la catégorie lisible des offres déjà classées.
    tampon = []
    for offre in Offre.objects.filter(secteur=secteur.code).only("id", "nature"):
        offre.categorie = f"{nom} - {(offre.nature or 'marche').capitalize()}"
        tampon.append(offre)
        if len(tampon) >= 500:
            Offre.objects.bulk_update(tampon, ["categorie"], batch_size=500)
            tampon = []
    if tampon:
        Offre.objects.bulk_update(tampon, ["categorie"], batch_size=500)
    return f"Secteur renommé « {nom} »."


def basculer_secteur(secteur) -> str:
    secteur.actif = not secteur.actif
    secteur.save(update_fields=["actif"])
    return (f"Secteur « {secteur.nom} » activé dans les filtres et le tri."
            if secteur.actif else
            f"Secteur « {secteur.nom} » désactivé; les offres existantes sont conservées.")


def retirer_secteur(secteur) -> str:
    # Archivage plutôt que suppression physique : l'IA ne le reproposera pas,
    # et l'utilisateur peut restaurer un code sans perdre l'historique.
    utilise = Offre.objects.filter(secteur=secteur.code).exists()
    secteur.actif = False
    secteur.save(update_fields=["actif"])
    if utilise:
        return (f"Secteur « {secteur.nom} » supprimé des choix actifs. "
                "Les offres déjà classées sont conservées; il peut être réactivé.")
    return f"Secteur « {secteur.nom} » retiré du catalogue; il peut être réactivé."


def creer_pays(nom) -> str:
    nom = _nom(nom)
    code = code_pays(nom)
    if not nom or not code:
        raise ValueError("Nom de pays invalide.")
    pays, cree = Pays.objects.get_or_create(code=code, defaults={"nom": nom})
    if not cree and pays.actif:
        raise ValueError(f"« {pays.nom} » existe déjà.")
    if not cree:
        pays.nom = nom
        pays.actif = True
        pays.save(update_fields=["nom", "actif"])
    return f"Pays « {nom} » ajouté au catalogue."


def renommer_pays(pays, nom) -> str:
    nom = _nom(nom)
    if not nom:
        raise ValueError("Le nom du pays ne peut pas être vide.")
    pays.nom = nom
    pays.save(update_fields=["nom"])
    return f"Libellé du pays modifié en « {nom} ». Les lieux déjà enregistrés restent inchangés."


def basculer_pays(pays) -> str:
    pays.actif = not pays.actif
    pays.save(update_fields=["actif"])
    return (f"Pays « {pays.nom} » activé dans les filtres."
            if pays.actif else
            f"Pays « {pays.nom} » désactivé des filtres; les offres sont conservées.")


def retirer_pays(pays) -> str:
    pays.actif = False
    pays.save(update_fields=["actif"])
    return f"Pays « {pays.nom} » retiré des choix actifs; les offres sont conservées."


# ------------------------------------------------------------ cles d'API

def creer_cle(nom) -> str:
    """Cree une cle et renvoie le jeton, montre UNE fois : seule son empreinte est gardee."""
    nom = str(nom or "").strip()[:80]
    if not nom:
        raise ValueError("Nom vide.")
    if CleApi.objects.filter(nom=nom).exists():
        raise ValueError(f"Une clé « {nom} » existe déjà.")
    jeton = engendrer()
    CleApi.objects.create(nom=nom, empreinte=empreinte(jeton))
    return jeton


# ---------------------------------------------------------------- taches

def lancer_tache(nom) -> tuple:
    """Une tache de fond a la fois. Renvoie (tache, message, niveau) ; niveau "info"
    si une autre tache tournait deja (c'est elle qui est renvoyee)."""
    if nom not in Tache.TYPES:
        raise ValueError("Action inconnue.")
    try:
        tache, _ = demarrer(nom)
    except DejaEnCours as exc:
        return exc.tache, f"Déjà en cours : {exc.tache.libelle}.", "info"
    except OSError as exc:
        raise ValueError(f"Lancement impossible : {exc}")
    return tache, f"{tache.libelle} : démarrage.", "succes"


def reprendre_tache(tache) -> tuple:
    """Relance une tache interrompue ou suspendue. Renvoie (tache, message, niveau)."""
    try:
        lance = reprendre(tache, manuel=True)
    except DejaEnCours as exc:
        return exc.tache, f"Déjà en cours : {exc.tache.libelle}.", "info"
    except OSError as exc:
        raise ValueError(f"Reprise impossible : {exc}")
    return lance[0], f"{tache.libelle} : reprise.", "succes"


def arreter_tache(tache, action) -> str:
    """Suspendre ou annuler UNE tache."""
    lot = Tache.objects.filter(pk=tache.pk)
    if action == "suspendre" and tache.statut == Tache.EN_COURS:
        Tache.arreter(lot, Tache.SUSPENDUE,
                      f"Suspendue pendant « {tache.etape} » : reprendra au même point.")
        return f"{tache.libelle} : suspension (effective sous 5 s)."
    if action == "annuler" and tache.statut in (Tache.EN_COURS, *Tache.EN_ATTENTE):
        Tache.arreter(lot, Tache.ANNULEE, f"Annulée pendant « {tache.etape} ».")
        return f"{tache.libelle} : annulation (effective sous 5 s)."
    raise ValueError(f"Impossible de {action} une tâche {tache.get_statut_display().lower()}.")


def agir_sur_toutes(action) -> tuple:
    """Tout suspendre (automatismes compris), tout annuler, tout reprendre.
    Renvoie (message, tache a reprendre ou None) : la reprise, elle, passe par
    `reprendre_tache`, une tache a la fois (les suivantes par le planificateur)."""
    reglages = Parametres.charger()
    actives = Tache.objects.filter(statut__in=(Tache.EN_COURS, *Tache.EN_ATTENTE))
    if action == "suspendre":
        Parametres.objects.filter(pk=reglages.pk).update(automatismes_suspendus=True)
        n = Tache.arreter(actives.exclude(statut=Tache.SUSPENDUE), Tache.SUSPENDUE,
                          "Suspendue (tout suspendre) : reprendra au même point.")
        return f"Tout est suspendu : {n} tâche(s), collecte automatique et reprises en pause.", None
    if action == "annuler":
        n = Tache.arreter(actives, Tache.ANNULEE, "Annulée (tout annuler).")
        return f"{n} tâche(s) annulée(s).", None
    if action == "reprendre":
        Parametres.objects.filter(pk=reglages.pk).update(automatismes_suspendus=False)
        suspendues = list(Tache.objects.filter(statut=Tache.SUSPENDUE).order_by("debut"))
        Tache.objects.filter(pk__in=[t.pk for t in suspendues[1:]]).update(statut=Tache.INTERROMPUE)
        return "Automatismes réactivés.", (suspendues[0] if suspendues else None)
    raise ValueError("Action inconnue.")
