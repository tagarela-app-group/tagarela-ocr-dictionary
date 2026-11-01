import os
from pathlib import Path

from config.environment import PRD, is_truthy, load_environment, split_csv


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def env_bool(name: str, default: bool) -> bool:
    return is_truthy(os.environ.get(name, str(default)))


BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT = load_environment(os.environ)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-dev-secret-key")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = split_csv(os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"))

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
    "apps.courses",
    "apps.captures",
    "apps.vocabulary",
    "apps.language_analysis",
    "apps.cards",
    "apps.exercises",
    "apps.reviews",
    "apps.daily_words",
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
        "OPTIONS": {
            "connect_timeout": env_int("POSTGRES_CONNECT_TIMEOUT", 5),
            "sslmode": os.environ.get("POSTGRES_SSLMODE", "prefer"),
        },
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
AUTH_CODE_TTL_SECONDS = env_int("AUTH_CODE_TTL_SECONDS", 15 * 60)
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
HEADLESS_JWT_ACCESS_TOKEN_EXPIRES_IN = env_int("AUTH_ACCESS_TOKEN_TTL_SECONDS", 300)
HEADLESS_JWT_REFRESH_TOKEN_EXPIRES_IN = env_int("AUTH_REFRESH_TOKEN_TTL_SECONDS", 30 * 24 * 60 * 60)

EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_TIMEOUT = env_int("EMAIL_TIMEOUT", 10)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Tagarela <nao-responda@localhost>")

CAPTURE_MAX_TEXT_LENGTH = 2000
CAPTURE_MAX_TERMS = 50
CAPTURE_MAX_TERM_LENGTH = 100
CAPTURE_PAGE_SIZE = env_int("CAPTURE_PAGE_SIZE", 50)

VOCABULARY_GROUP_NAME_MAX_LENGTH = env_int("VOCABULARY_GROUP_NAME_MAX_LENGTH", 30)

LANGUAGE_ANALYSIS_MAX_TEXT_LENGTH = env_int("LANGUAGE_ANALYSIS_MAX_TEXT_LENGTH", 3000)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_TIMEOUT = env_int("GEMINI_TIMEOUT", 30)

TERM_CARD_MAX_CAPTURES = env_int("TERM_CARD_MAX_CAPTURES", 10)
EXERCISE_VARIATIONS = env_int("EXERCISE_VARIATIONS", 3)
REVIEW_SESSION_SIZE = env_int("REVIEW_SESSION_SIZE", 10)
DAILY_WORD_AVOID_LIMIT = env_int("DAILY_WORD_AVOID_LIMIT", 200)

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
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
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if ENVIRONMENT == PRD:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^health$"]
    SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 365 * 24 * 60 * 60)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
