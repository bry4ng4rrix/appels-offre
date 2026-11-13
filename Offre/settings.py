"""Reglages du projet Django "Appels d'offres".

Tout se lit depuis l'environnement (.env a la racine). Les constantes des
sources de collecte vivent dans Offre/sources.py et sont importees ici.
"""

import os
import secrets
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

from .sources import *  # noqa: F401,F403 -- URLs, delais et plafonds des scrapers

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _vrai(nom: str, defaut: str = "") -> bool:
    return os.environ.get(nom, defaut).strip().lower() in {"1", "true", "yes", "on"}


DEBUG = _vrai("DEBUG", "true")

# SECRET_KEY de l'environnement si elle existe ; sinon une cle aleatoire est
# engendree une fois et conservee dans .secret_key (hors git), pour que les
# sessions survivent au redemarrage. Valable aussi dans le conteneur Docker.
FICHIER_CLE = BASE_DIR / ".secret_key"


def _cle_de_signature() -> str:
    cle = os.environ.get("SECRET_KEY", "").strip()
    if cle and cle != "change-me-in-production-random-secret-key-here":
        return cle
    if FICHIER_CLE.exists() and FICHIER_CLE.read_text().strip():
        return FICHIER_CLE.read_text().strip()
    cle = secrets.token_urlsafe(50)
    FICHIER_CLE.write_text(cle)
    return cle


SECRET_KEY = _cle_de_signature()

ALLOWED_HOSTS = [h.strip() for h in
                 os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
                 if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.offres",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "Offre.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "Offre.wsgi.application"


# --- Base de donnees ---
# Port 5434 : 5432 et 5433 sont pris par d'autres projets sur la machine de dev.
# sqlite:///chemin est accepte pour essayer le projet sans PostgreSQL.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://veille:veille@127.0.0.1:5434/veille")


def _base_depuis_url(url: str) -> dict:
    u = urlparse(url)
    if u.scheme == "sqlite":
        return {"ENGINE": "django.db.backends.sqlite3",
                "NAME": u.path[1:] or BASE_DIR / "db.sqlite3"}  # sqlite:////abs ou sqlite:///rel
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": (u.path or "/").lstrip("/"),
        "USER": unquote(u.username or ""),
        "PASSWORD": unquote(u.password or ""),
        "HOST": u.hostname or "127.0.0.1",
        "PORT": str(u.port or 5432),
    }


DATABASES = {"default": _base_depuis_url(DATABASE_URL)}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Indian/Antananarivo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"


# --- Securite derriere un proxy TLS (production) ---
DERRIERE_TLS = _vrai("DERRIERE_TLS")
if DERRIERE_TLS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = DERRIERE_TLS
CSRF_COOKIE_SECURE = DERRIERE_TLS
SECURE_HSTS_SECONDS = 31536000 if DERRIERE_TLS else 0
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_TRUSTED_ORIGINS = [o.strip() for o in
                        os.environ.get("CSRF_TRUSTED_ORIGINS",
                                       "http://127.0.0.1:8000,http://localhost:8000").split(",")
                        if o.strip()]


# --- Collecte automatique quotidienne (manage.py planifier) ---
# Heure locale (TIME_ZONE) du traitement complet : collecte, tri, liens.
VEILLE_HEURE = os.environ.get("VEILLE_HEURE", "06:00").strip()


# --- API publique (/api/public/, sans jeton) ---
# UNjobnet et la BAD interdisent la rediffusion sans accord ecrit : les
# lister ici les retire du namespace public. Vide = tout est expose.
API_PUBLIQUE_SOURCES_EXCLUES = [s.strip() for s in
                                os.environ.get("API_PUBLIQUE_SOURCES_EXCLUES", "").split(",")
                                if s.strip()]
API_PUBLIQUE_ORIGINES = os.environ.get("API_PUBLIQUE_ORIGINES", "*").strip()


# --- Notification email ---
# Sans SMTP_HOST, les emails partent sur la console : rien n'est perdu en
# developpement, et le recapitulatif reste lisible dans le journal.
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
NOTIFY_TO = [a.strip() for a in os.environ.get("NOTIFY_TO", "").split(",") if a.strip()]
DEFAULT_FROM_EMAIL = os.environ.get("SMTP_USER", "").strip() or "veille@localhost"
MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {
            "host": SMTP_HOST,
            "port": int(os.environ.get("SMTP_PORT") or 587),
            "username": os.environ.get("SMTP_USER", ""),
            "password": os.environ.get("SMTP_PASSWORD", ""),
            "use_tls": True,
        },
    } if SMTP_HOST else {"BACKEND": "django.core.mail.backends.console.EmailBackend"},
}
