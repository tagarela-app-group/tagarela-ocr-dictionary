import os
from pathlib import Path

from config.environment import PRD, is_truthy, load_environment, split_csv


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def env_floats(name: str, default: str) -> tuple[float, ...]:
    return tuple(float(value) for value in split_csv(os.environ.get(name, default)))


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
REVIEW_SECONDS_PER_DAY = env_int("REVIEW_SECONDS_PER_DAY", 86400)
REVIEW_DATE_TOLERANCE_DAYS = env_int("REVIEW_DATE_TOLERANCE_DAYS", 1)
REVIEW_POINTS_READ = env_float("REVIEW_POINTS_READ", 10)
REVIEW_POINTS_LISTEN = env_float("REVIEW_POINTS_LISTEN", 15)
REVIEW_POINTS_PRODUCE = env_float("REVIEW_POINTS_PRODUCE", 20)
REVIEW_RESULT_FIRST = env_float("REVIEW_RESULT_FIRST", 1)
REVIEW_RESULT_HINT = env_float("REVIEW_RESULT_HINT", 0.5)
REVIEW_RESULT_RETRY = env_float("REVIEW_RESULT_RETRY", 0.3)
REVIEW_RESULT_MISSED = env_float("REVIEW_RESULT_MISSED", 0)
REVIEW_SEEN_SENTENCE = env_float("REVIEW_SEEN_SENTENCE", 0.8)
REVIEW_SLOW_SUPPORT = env_float("REVIEW_SLOW_SUPPORT", 0.8)
REVIEW_CARD_POINTS = env_float("REVIEW_CARD_POINTS", 1)
REVIEW_FAIR_POINTS = env_float("REVIEW_FAIR_POINTS", 4)
REVIEW_GOOD_POINTS = env_float("REVIEW_GOOD_POINTS", 8)
REVIEW_GREAT_POINTS = env_float("REVIEW_GREAT_POINTS", 15)
REVIEW_GROWTH_POINTS = env_floats("REVIEW_GROWTH_POINTS", "0,4,8,10,15,20")
REVIEW_GROWTH_FACTORS = env_floats("REVIEW_GROWTH_FACTORS", "0.25,0.5,1.25,2,2.5,3")
REVIEW_MAX_GROWTH = env_float("REVIEW_MAX_GROWTH", 4)
REVIEW_TIME_MIN = env_float("REVIEW_TIME_MIN", 0.25)
REVIEW_TIME_MAX = env_float("REVIEW_TIME_MAX", 2)
REVIEW_START_INTERVAL_DAYS = env_float("REVIEW_START_INTERVAL_DAYS", 2)
REVIEW_MIN_INTERVAL_DAYS = env_float("REVIEW_MIN_INTERVAL_DAYS", 1)
REVIEW_MAX_INTERVAL_DAYS = env_float("REVIEW_MAX_INTERVAL_DAYS", 180)
REVIEW_FIRST_REVIEW_DAYS = env_float("REVIEW_FIRST_REVIEW_DAYS", 1)
REVIEW_JITTER = env_float("REVIEW_JITTER", 0.1)
REVIEW_RETEST_BASE_HOURS = env_float("REVIEW_RETEST_BASE_HOURS", 4)
REVIEW_RETEST_HOURS_PER_POINT = env_float("REVIEW_RETEST_HOURS_PER_POINT", 2)
REVIEW_EASE_MIN = env_float("REVIEW_EASE_MIN", 0.75)
REVIEW_EASE_MAX = env_float("REVIEW_EASE_MAX", 1.25)
REVIEW_EASE_DROP = env_float("REVIEW_EASE_DROP", 0.1)
REVIEW_EASE_GAIN = env_float("REVIEW_EASE_GAIN", 0.03)
REVIEW_LEVEL_DAYS = env_floats("REVIEW_LEVEL_DAYS", "4,8,16,24,30")
REVIEW_CAPACITY_START = env_int("REVIEW_CAPACITY_START", 10)
REVIEW_CAPACITY_MIN = env_int("REVIEW_CAPACITY_MIN", 5)
REVIEW_CAPACITY_MAX = env_int("REVIEW_CAPACITY_MAX", 25)
REVIEW_CAPACITY_UP = env_int("REVIEW_CAPACITY_UP", 2)
REVIEW_CAPACITY_DOWN = env_int("REVIEW_CAPACITY_DOWN", 1)
REVIEW_FORECAST_DAYS = env_int("REVIEW_FORECAST_DAYS", 7)
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
