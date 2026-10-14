"""
Django settings for financeeasy project.

Sistema de Gestão Financeira — MVP baseado na persona
"O Equilibrista Sobrecarregado".
"""

import os
from pathlib import Path

import dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis de ambiente do arquivo .env (veja .env.example)
dotenv.load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-financeeasy-dev-key-troque-em-producao",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()
]

# Necessario quando o app e acessado por tras de um tunel/proxy HTTPS
# (ngrok, Cloudflare Tunnel, etc.) - o Django exige que a origem exata
# (com esquema https://) esteja nesta lista para aceitar POSTs (login,
# cadastro, formularios) vindos de um dominio diferente de localhost.
# Ex.: DJANGO_CSRF_TRUSTED_ORIGINS=https://meu-tunel.trycloudflare.com
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Apps do FinanceEasy
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


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

_db_path = os.getenv("DJANGO_DB_PATH")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(_db_path) if _db_path else BASE_DIR / "db.sqlite3",
    }
}

# Usuário customizado (login por e-mail — RF02)
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:painel"
LOGOUT_REDIRECT_URL = "accounts:login"


# Internationalization — RNF01/RNF02: usuário brasileiro, linguagem simples
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cache simples em memória — usado para não estourar a cota diária da
# API gratuita da HG Brasil (RNF08/RNF07: desempenho e escalabilidade).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "financeeasy-cache",
    }
}

# ---------------------------------------------------------------------------
# Integrações externas (arquitetura obrigatória do projeto)
# ---------------------------------------------------------------------------

# HG Brasil Finance API (https://hgbrasil.com/finance/) — plano free (400 req/dia).
# Deixe em branco em desenvolvimento: o dashboard mostra um aviso e segue
# funcionando normalmente até a chave ser configurada (ver README.md).
HGBRASIL_API_KEY = os.getenv("HGBRASIL_API_KEY", "")
HGBRASIL_API_URL = "https://api.hgbrasil.com/finance"
HGBRASIL_CACHE_TTL_SECONDS = int(os.getenv("HGBRASIL_CACHE_TTL_SECONDS", "900"))  # 15 min

# Hugging Face Inference API — usada para classificar automaticamente a
# categoria das transações importadas do extrato (UC04/UC05).
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "")
HUGGINGFACE_ZERO_SHOT_MODEL = os.getenv(
    "HUGGINGFACE_ZERO_SHOT_MODEL", "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
)

# E-mail (recuperação de senha via OTP — UC01/FA02). Em desenvolvimento os
# e-mails são impressos no console.
EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL", "contato@financeeasy.local")

MESSAGE_TAGS = {
    10: "info",  # DEBUG
    20: "info",  # INFO
    25: "success",  # SUCCESS
    30: "warning",  # WARNING
    40: "danger",  # ERROR
}
