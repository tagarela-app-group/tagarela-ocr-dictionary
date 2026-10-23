import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-dev-secret-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.accounts",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",
    "allauth.headless",
    "apps.ocr",
    "apps.lexical",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "tagarela"),
        "USER": os.environ.get("POSTGRES_USER", "tagarela"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "tagarela"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

ACCOUNT_ADAPTER = "apps.accounts.adapters.AccountAdapter"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_SIGNUP_FORM_CLASS = "apps.accounts.forms.SignupForm"
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = True
ACCOUNT_PASSWORD_RESET_BY_CODE_ENABLED = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False
AUTH_CODE_TTL_SECONDS = int(os.environ.get("AUTH_CODE_TTL_SECONDS", str(15 * 60)))
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT = AUTH_CODE_TTL_SECONDS
ACCOUNT_PASSWORD_RESET_BY_CODE_TIMEOUT = AUTH_CODE_TTL_SECONDS
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Tagarela] "
ALLAUTH_USER_CODE_FORMAT = {"length": 6, "numeric": True, "dashed": False}

SOCIALACCOUNT_ADAPTER = "apps.accounts.adapters.SocialAccountAdapter"
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
APPLE_CLIENT_ID = os.environ.get("APPLE_CLIENT_ID", "")
SOCIALACCOUNT_PROVIDERS = {
    "google": {"APPS": [{"client_id": GOOGLE_CLIENT_ID, "secret": ""}] if GOOGLE_CLIENT_ID else []},
    "apple": {"APPS": [{"client_id": APPLE_CLIENT_ID, "secret": ""}] if APPLE_CLIENT_ID else []},
}

HEADLESS_ONLY = True
HEADLESS_ADAPTER = "apps.accounts.adapters.HeadlessAdapter"
HEADLESS_CLIENTS = ("app",)
HEADLESS_TOKEN_STRATEGY = "allauth.headless.tokens.strategies.jwt.JWTTokenStrategy"
HEADLESS_JWT_ALGORITHM = "HS256"
HEADLESS_JWT_ACCESS_TOKEN_EXPIRES_IN = int(os.environ.get("AUTH_ACCESS_TOKEN_TTL_SECONDS", "300"))
HEADLESS_JWT_REFRESH_TOKEN_EXPIRES_IN = int(
    os.environ.get("AUTH_REFRESH_TOKEN_TTL_SECONDS", str(30 * 24 * 60 * 60))
)

EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() in {"1", "true", "yes", "on"}
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Tagarela <nao-responda@localhost>")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

OCR_MAX_IMAGE_SIZE_BYTES = int(os.environ.get("OCR_MAX_IMAGE_SIZE_BYTES", str(10 * 1024 * 1024)))
OCR_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
OCR_ALLOWED_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
}

LEXICAL_LANGUAGE = os.environ.get("LEXICAL_LANGUAGE", "en")
LEXICAL_CACHE_TTL_SECONDS = int(os.environ.get("LEXICAL_CACHE_TTL_SECONDS", str(24 * 60 * 60)))
DICTIONARY_API_BASE_URL = os.environ.get(
    "DICTIONARY_API_BASE_URL",
    "https://api.dictionaryapi.dev/api/v2/entries",
)
DICTIONARY_API_TIMEOUT_SECONDS = float(os.environ.get("DICTIONARY_API_TIMEOUT_SECONDS", "5"))

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "allauth.headless.contrib.rest_framework.authentication.JWTTokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
