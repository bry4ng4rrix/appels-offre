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
    "django.contrib.humanize",
    "apps.offres",
    # Comptes : email + mot de passe, Google, verification, reinitialisation.
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Tout exige une session, sauf les vues marquees @login_not_required
    # (connexion, API a jeton, API publique).
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "allauth.account.middleware.AccountMiddleware",
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
                "apps.offres.context_processors.guide",
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

# --- Comptes (django-allauth) ---
# ADMIN = is_staff (cree par `manage.py creer_admin`), USER = tout autre compte.
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # /admin/ par identifiant
    "allauth.account.auth_backends.AuthenticationBackend",  # site par email
]
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "web-liste"
# Juste apres l'inscription (email ou Google) : completer le profil.
ACCOUNT_SIGNUP_REDIRECT_URL = "/profil/?bienvenue=1"
ACCOUNT_LOGOUT_REDIRECT_URL = "public-vitrine"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_UNIQUE_EMAIL = True
# shortcut: verification coupee tant que l'envoi d'email n'est pas configure ;
# repasser a "mandatory" avant les alertes email (sinon n'importe qui inscrit l'adresse d'un autre).
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_CONFIRM_EMAIL_ON_GET = False  # un POST : un antivirus qui suit le lien ne valide rien
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_SESSION_REMEMBER = None  # case « Rester connecte »
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Label Collectes] "
ACCOUNT_ADAPTER = "apps.offres.comptes.CompteAdapter"
# Limites par defaut d'allauth : 5 echecs de connexion / 5 min par compte,
# 10 / min par IP ; elles s'appuient sur le cache ci-dessous.
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True  # email verifie par Google = meme compte
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": [{
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", "").strip(),
            "secret": os.environ.get("GOOGLE_CLIENT_SECRET", "").strip(),
        }] if os.environ.get("GOOGLE_CLIENT_ID", "").strip() else [],
        "SCOPE": ["openid", "profile", "email"],
        "AUTH_PARAMS": {"access_type": "online", "prompt": "select_account"},
    },
}

# Cache en base : partage entre les workers gunicorn (limites de connexion).
# La table se cree avec `manage.py createcachetable`.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache",
                      "LOCATION": "cache_django"}}

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Indian/Antananarivo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Fichiers deposes (CV, photos de profil) ---
# PRIVES : aucune route ne sert MEDIA_ROOT (ne jamais ajouter static(MEDIA_URL...)).
# Ils ne sortent que par les vues de views_profil, qui verifient le proprietaire.
MEDIA_ROOT = Path(os.environ.get("FICHIERS_PRIVES") or BASE_DIR / "prive")

# Adresse publique du site, pour les liens des emails d'alerte (pas de requete
# HTTP dans le planificateur pour la deviner). Ex. https://veille.exemple.org
SITE_URL = os.environ.get("SITE_URL", "").strip().rstrip("/")


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
# Valeur initiale seulement : elle se regle ensuite dans l'onglet Parametres.
VEILLE_HEURE = os.environ.get("VEILLE_HEURE", "06:00").strip()

# Qualification sémantique facultative par Ollama. Le moteur déterministe
# reste le secours si le service local est injoignable ou renvoie une sortie invalide.
CLASSIFICATEUR_IA = os.environ.get("CLASSIFICATEUR_IA", "off").strip().lower()
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:1b").strip()
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "45"))


# Nombre de sources collectees (et de sources dont les liens sont verifies)
# en meme temps. Chaque source garde ses propres delais de politesse.
COLLECTE_PARALLELE = int(os.environ.get("COLLECTE_PARALLELE") or 4)


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
