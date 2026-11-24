"""Variables communes à toutes les pages."""

from django.utils.functional import SimpleLazyObject


def guide(requete):
    """`guide_auto` : le guide de la page démarre seul (première visite d'un utilisateur).

    Paresseux : la requête n'est faite que si un gabarit lit la variable (base.html),
    pas pour les fragments HTMX. Les admins le lancent eux-mêmes avec le bouton « ? ».
    """
    def calculer():
        user = getattr(requete, "user", None)
        if not (user and user.is_authenticated) or user.is_staff or not requete.resolver_match:
            return False
        from apps.offres.models import Profil
        vus = Profil.objects.filter(user=user).values_list("guides_vus", flat=True).first() or []
        return requete.resolver_match.url_name not in vus
    return {"guide_auto": SimpleLazyObject(calculer)}


def css(requete):
    """`debug_css` : en DEBUG, Tailwind compile dans le navigateur ; sinon la
    feuille construite au build Docker est servie (voir base.html)."""
    from django.conf import settings
    return {"debug_css": settings.DEBUG}
