"""Recapitulatif des offres retenues : texte (copie, email) et envoi SMTP."""

from django.conf import settings
from django.core.mail import send_mail


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

    @classmethod
    def envoyer_email(cls, offres) -> bool:
        """Envoie le recapitulatif a NOTIFY_TO. Renvoie False si rien n'est parti."""
        if not offres:
            print("Aucune opportunite pertinente, pas d'email envoye.")
            return False
        if not settings.NOTIFY_TO:
            print("NOTIFY_TO vide dans .env : email non envoye (resultats en base).")
            return False
        send_mail(f"Veille appels/emplois : {len(offres)} nouveaute(s)",
                  cls.construire_corps(offres), settings.DEFAULT_FROM_EMAIL,
                  settings.NOTIFY_TO)
        print(f"Email envoye a {', '.join(settings.NOTIFY_TO)} ({len(offres)} offre(s)).")
        return True
