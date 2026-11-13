from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("comptes/", include("django.contrib.auth.urls")),
    path("", include("apps.offres.urls")),
]

if not settings.DEBUG:
    # shortcut: Django sert lui-meme les statiques (une feuille CSS, l'admin) ;
    # suffisant derriere le tunnel SSH, a confier a nginx si l'interface devient publique.
    urlpatterns.insert(0, re_path(r"^static/(?P<path>.*)$", serve,
                                  {"document_root": settings.STATIC_ROOT}))
