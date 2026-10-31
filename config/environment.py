from collections.abc import Mapping

from django.core.exceptions import ImproperlyConfigured

DSV = "dsv"
PRD = "prd"

SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
PLACEHOLDERS = {"", "change-me", "example", "tagarela", "unsafe-dev-secret-key"}
LOCAL_HOSTS = {"*", "0.0.0.0", "10.0.2.2", "127.0.0.1", "db", "localhost", "mailpit"}


def is_truthy(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on"}


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_real_host(host: str) -> bool:
    return bool(host) and host not in LOCAL_HOSTS and not host.endswith(".invalid")


def prd_problems(env: Mapping[str, str]) -> list[str]:
    hosts = split_csv(env.get("DJANGO_ALLOWED_HOSTS", ""))
    from_domain = env.get("DEFAULT_FROM_EMAIL", "").rstrip(">").rpartition("@")[2]
    checks = {
        "DJANGO_SECRET_KEY": env.get("DJANGO_SECRET_KEY", "") not in PLACEHOLDERS,
        "DJANGO_DEBUG": not is_truthy(env.get("DJANGO_DEBUG", "")),
        "DJANGO_ALLOWED_HOSTS": bool(hosts) and all(_is_real_host(host) for host in hosts),
        "POSTGRES_PASSWORD": env.get("POSTGRES_PASSWORD", "") not in PLACEHOLDERS,
        "GEMINI_API_KEY": bool(env.get("GEMINI_API_KEY", "")),
        "EMAIL_BACKEND": env.get("EMAIL_BACKEND", "") == SMTP_BACKEND,
        "EMAIL_HOST": _is_real_host(env.get("EMAIL_HOST", "")),
        "DEFAULT_FROM_EMAIL": _is_real_host(from_domain),
    }
    return [name for name, is_valid in checks.items() if not is_valid]


def load_environment(env: Mapping[str, str]) -> str:
    name = env.get("DJANGO_ENV", "")
    if name not in {DSV, PRD}:
        raise ImproperlyConfigured("DJANGO_ENV precisa ser dsv ou prd.")
    if name == PRD and (problems := prd_problems(env)):
        raise ImproperlyConfigured(f"Configuração de prd inválida: {', '.join(problems)}.")
    return name
