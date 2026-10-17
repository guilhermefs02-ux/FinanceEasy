"""
Django settings for financeeasy project.

Sistema de Gestão Financeira — MVP baseado na persona
"O Equilibrista Sobrecarregado".
"""

import os
from pathlib import Path

import dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis de ambiente do arquivo .env local.
# No Render, as variáveis podem ser configuradas no painel do serviço.
dotenv.load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Configurações gerais e segurança
# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-financeeasy-dev-key-troque-em-producao",
)

DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1",
    ).split(",")
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "",
    ).split(",")
    if o.strip()
]


# ---------------------------------------------------------------------------
# Limites de upload e importação de arquivos
# ---------------------------------------------------------------------------

MAX_UPLOAD_SIZE_MB = int(
    os.getenv("DJANGO_MAX_UPLOAD_SIZE_MB", "10")
)
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

DATA_UPLOAD_MAX_MEMORY_SIZE = int(
    os.getenv("DJANGO_MAX_REQUEST_SIZE_MB", "12")
) * 1024 * 1024

DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000
FILE_UPLOAD_MAX_MEMORY_SIZE = 2_621_440


# ---------------------------------------------------------------------------
# Aplicativos
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
    "accounts",
    "transactions",
    "debts",
    "goals",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "core.middleware.TunnelBasicAuthMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.DailyDueDateScanMiddleware",
]

ROOT_URLCONF = "financeeasy.urls"

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
                "core.context_processors.privacy_mode",
                "core.context_processors.notificacoes",
            ],
        },
    },
]

WSGI_APPLICATION = "financeeasy.wsgi.application"


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------

_db_path = os.getenv("DJANGO_DB_PATH")
_database_url = os.getenv("DATABASE_URL")

if _database_url:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(
            _database_url,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": (
                Path(_db_path)
                if _db_path
                else BASE_DIR / "db.sqlite3"
            ),
        }
    }


# Usuário customizado: login por e-mail.
AUTH_USER_MODEL = "accounts.User"


# ---------------------------------------------------------------------------
# Validação de senhas
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:painel"
LOGOUT_REDIRECT_URL = "accounts:login"


# ---------------------------------------------------------------------------
# Internacionalização
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Arquivos estáticos e enviados
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "financeeasy-cache",
    }
}


# ---------------------------------------------------------------------------
# Integrações externas
# ---------------------------------------------------------------------------

# HG Brasil Finance API
HGBRASIL_API_KEY = os.getenv("HGBRASIL_API_KEY", "")
HGBRASIL_API_URL = "https://api.hgbrasil.com/finance"
HGBRASIL_CACHE_TTL_SECONDS = int(
    os.getenv("HGBRASIL_CACHE_TTL_SECONDS", "900")
)

# Groq API — categorização automática de despesas.
# Configure GROQ_API_KEY nas variáveis de ambiente do Render.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b",
)

try:
    GROQ_TIMEOUT_SECONDS = float(
        os.getenv("GROQ_TIMEOUT_SECONDS", "8")
    )
except (TypeError, ValueError):
    GROQ_TIMEOUT_SECONDS = 8.0

GROQ_TIMEOUT_SECONDS = max(
    1.0,
    min(GROQ_TIMEOUT_SECONDS, 20.0),
)


# ---------------------------------------------------------------------------
# E-mail — recuperação de senha via OTP
# ---------------------------------------------------------------------------

EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.getenv(
    "DJANGO_DEFAULT_FROM_EMAIL",
    "contato@financeeasy.local",
)

MESSAGE_TAGS = {
    10: "info",
    20: "info",
    25: "success",
    30: "warning",
    40: "danger",
}


# ---------------------------------------------------------------------------
# Logs de diagnóstico para produção (Render)
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "goals": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
