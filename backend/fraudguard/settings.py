"""
Configuration Django — FraudGuard
"""

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        # En production, refuser de démarrer plutôt que d'utiliser une clé connue.
        raise ImproperlyConfigured("DJANGO_SECRET_KEY doit être définie quand DJANGO_DEBUG=False.")
    SECRET_KEY = "insecure-dev-key-change-me"

ALLOWED_HOSTS = [
    hote.strip()
    for hote in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if hote.strip()
]
# Render fournit le nom d'hôte public du service (ex. fraudguard-api.onrender.com).
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Tiers
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
    "django_filters",
    # Apps internes (alignees sur le diagramme de packages)
    "authentication",
    "transactions",
    "fraud_detection",
    "alerts",
    "reports",
    "audit",
    "dashboard",
]

MIDDLEWARE = [
    # En premier : répond à /api/health/ avant ALLOWED_HOSTS et la redirection HTTPS.
    "fraudguard.middleware.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Sert les fichiers statiques (admin, Swagger) sans serveur web séparé.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "audit.middleware.AuditLogMiddleware",
]

ROOT_URLCONF = "fraudguard.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "fraudguard.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "fraudguard"),
        "USER": os.getenv("POSTGRES_USER", "fraudguard"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "fraudguard"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}
# Sur Render, la base est fournie sous forme d'URL unique :
# postgresql://utilisateur:motdepasse@hote:port/base
if os.getenv("DATABASE_URL"):
    _url = urlparse(os.environ["DATABASE_URL"])
    DATABASES["default"].update({
        "NAME": unquote(_url.path.lstrip("/")),
        "USER": unquote(_url.username or ""),
        "PASSWORD": unquote(_url.password or ""),
        "HOST": _url.hostname or "",
        "PORT": str(_url.port or 5432),
        "CONN_MAX_AGE": 60,
    })

AUTH_USER_MODEL = "authentication.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Dakar"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "media/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # En production : fichiers compressés et versionnés (après collectstatic).
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- REST Framework ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "FraudGuard API",
    "DESCRIPTION": "API de detection de fraude bancaire",
    "VERSION": "1.0.0",
    # Noms explicites pour les différents champs "status" dans Swagger.
    "ENUM_NAME_OVERRIDES": {
        "TransactionStatusEnum": "transactions.models.Transaction.Status",
        "AlertStatusEnum": "alerts.models.Alert.Status",
    },
}

# Origines autorisées à appeler l'API (frontend React). Liste séparée par des
# virgules dans le .env, ex. : http://localhost:3000,https://fraudguard.onrender.com
CORS_ALLOWED_ORIGINS = [
    origine.strip()
    for origine in os.getenv(
        "DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001"
    ).split(",")
    if origine.strip()
]
# Nécessaire pour les formulaires POST (connexion à /admin/) servis en HTTPS.
CSRF_TRUSTED_ORIGINS = [
    origine.strip()
    for origine in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origine.strip()
]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# --- HTTPS obligatoire en production (CDC §6 Sécurité, §9 chiffrement en transit) ---
# Actif dès que DJANGO_DEBUG=False ; chaque réglage reste surchargeable par
# variable d'environnement (ex. DJANGO_SECURE_SSL_REDIRECT=False pour tester
# l'image de production en HTTP local avec docker compose).
def _env_bool(nom, defaut):
    return os.getenv(nom, str(defaut)) == "True"


PRODUCTION = not DEBUG
# Render termine le TLS sur son proxy et transmet X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = _env_bool("DJANGO_SECURE_SSL_REDIRECT", PRODUCTION)
# (/api/health/ est servi par fraudguard.middleware.HealthCheckMiddleware,
# avant cette redirection.)
SESSION_COOKIE_SECURE = _env_bool("DJANGO_SECURE_COOKIES", PRODUCTION)
CSRF_COOKIE_SECURE = _env_bool("DJANGO_SECURE_COOKIES", PRODUCTION)
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "3600" if PRODUCTION else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = False  # *.onrender.com ne nous appartient pas
# Avertissements HSTS volontairement ignorés : on ne peut ni imposer HSTS aux
# sous-domaines de onrender.com ni inscrire ce domaine à la liste preload.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Fichiers générés (rapports PDF/CSV, CDC 5.5)
MEDIA_ROOT = Path(os.getenv("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))
REPORTS_DIR = MEDIA_ROOT / "reports"

# --- Regle metier CDC 5.3 ---
FRAUD_ALERT_THRESHOLD = float(os.getenv("FRAUD_ALERT_THRESHOLD", "0.7"))

# --- Integration ML (dossier /ml, voir docker-compose.yml) ---
# ML_MODELS_DIR : ou se trouve fraudguard_pipeline.joblib (monte en lecture
#   seule par docker-compose, volume ./ml/models:/app/ml_models).
# ML_SRC_DIR : ou se trouve ml/src/preprocessing.py et predict.py (monte
#   par docker-compose, volume ./ml/src:/app/ml_src) — ajoute a sys.path
#   par fraud_detection/apps.py pour pouvoir faire `import preprocessing`.
ML_MODELS_DIR = os.getenv("ML_MODELS_DIR", str(BASE_DIR / "ml_models"))
ML_SRC_DIR = os.getenv("ML_SRC_DIR", str(BASE_DIR / "ml_src"))
