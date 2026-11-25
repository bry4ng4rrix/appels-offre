from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("comptes/", include("allauth.urls")),
    # Connexion des frontends en JSON (allauth headless), voir apps/offres/views_app.py.
    path("_allauth/", include("allauth.headless.urls")),
    path("", include("apps.offres.urls")),
]

if not settings.DEBUG:
    # shortcut: Django sert lui-meme les statiques (une feuille CSS, l'admin) ;
    # suffisant derriere le tunnel SSH, a confier a nginx si l'interface devient publique.
    # Publics : la page de connexion en a besoin.
    urlpatterns.insert(0, re_path(r"^static/(?P<path>.*)$", login_not_required(serve),
                                  {"document_root": settings.STATIC_ROOT}))
