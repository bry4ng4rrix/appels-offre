from django.apps import AppConfig


class OffresConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.offres"
    verbose_name = "Veille Appels d'Offres"

    def ready(self):
        from allauth.account.signals import user_signed_up

        from .inscription import enregistrer
        user_signed_up.connect(enregistrer, dispatch_uid="offres-inscription")
