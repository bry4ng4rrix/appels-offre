"""Recapitulatif des offres retenues : texte (copie, email) et envoi SMTP."""

from django.conf import settings
from django.core.mail import EmailMessage, mailers
from django.core.mail.backends.smtp import EmailBackend

from apps.offres.models import Parametres


class NotificationService:

    @staticmethod
    def construire_corps(offres) -> str:
        lignes = [f"{len(offres)} opportunite(s) pertinente(s)\n"]
        for o in offres:
            echeance = o.date_limite.strftime("%d/%m/%Y") if o.date_limite else "non precisee"
            lignes.append(
                f"[{o.source.upper()}] {o.titre}\n"
                f"{o.organisation or '-'} — {o.pays or '-'} — {o.categorie or ''}\n"
                f"Cloture : {echeance}\n{o.lien or ''}\n")
        return "\n".join(lignes)

    @staticmethod
    def configuration():
        """(mailer, expediteur, destinataires). L'onglet Parametres prime sur le .env."""
        p = Parametres.charger()
        destinataires = p.liste_destinataires() or settings.NOTIFY_TO
        if not p.smtp_hote:
            return mailers.default, settings.DEFAULT_FROM_EMAIL, destinataires
        # Construit comme le fait django.core.mail.mailers (alias = pas d'avertissement).
        mailer = EmailBackend(alias="parametres", host=p.smtp_hote, port=p.smtp_port,
                              username=p.smtp_utilisateur, password=p.smtp_mot_de_passe,
                              use_tls=p.smtp_securite == "tls", use_ssl=p.smtp_securite == "ssl",
                              timeout=20)
        return mailer, p.smtp_utilisateur or settings.DEFAULT_FROM_EMAIL, destinataires

    @classmethod
    def envoyer(cls, sujet: str, corps: str) -> list:
        """Envoie a tous les destinataires et les renvoie ([] : rien n'est parti).
        Les erreurs SMTP remontent a l'appelant."""
        _, _, destinataires = cls.configuration()
        if destinataires:
            cls.envoyer_a(destinataires, sujet, corps)
        return destinataires

    @classmethod
    def envoyer_a(cls, destinataires: list, sujet: str, corps: str):
        """Meme serveur que le recapitulatif, destinataires choisis (alertes)."""
        mailer, expediteur, _ = cls.configuration()
        mailer.send_messages([EmailMessage(sujet, corps, expediteur, destinataires)])

    @classmethod
    def envoyer_email(cls, offres) -> bool:
        """Envoie le recapitulatif. Renvoie False si rien n'est parti."""
        if not offres:
            print("Aucune opportunite pertinente, pas d'email envoye.")
            return False
        destinataires = cls.envoyer(f"Veille appels/emplois : {len(offres)} nouveaute(s)",
                                    cls.construire_corps(offres))
        if not destinataires:
            print("Aucun destinataire (onglet Parametres ou NOTIFY_TO) : email non envoye.")
            return False
        print(f"Email envoye a {', '.join(destinataires)} ({len(offres)} offre(s)).")
        return True
