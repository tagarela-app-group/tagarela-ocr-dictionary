from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.db.utils import OperationalError
from django.test import SimpleTestCase
from rest_framework.test import APISimpleTestCase

from config.environment import load_environment

VALID_PRD = {
    "DJANGO_ENV": "prd",
    "DJANGO_SECRET_KEY": "chave-de-verdade",
    "DJANGO_ALLOWED_HOSTS": "api.tagarela.test",
    "POSTGRES_PASSWORD": "senha-de-verdade",
    "GEMINI_API_KEY": "chave-de-verdade",
    "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
    "EMAIL_HOST": "smtp.tagarela.test",
    "DEFAULT_FROM_EMAIL": "Tagarela <nao-responda@tagarela.test>",
}


class LoadEnvironmentTests(SimpleTestCase):
    def test_refuses_missing_or_unknown_environment(self):
        for env in ({}, {"DJANGO_ENV": ""}, {"DJANGO_ENV": "stg"}):
            with self.subTest(env=env), self.assertRaises(ImproperlyConfigured):
                load_environment(env)

    def test_dsv_accepts_local_values(self):
        env = {"DJANGO_ENV": "dsv", "DJANGO_SECRET_KEY": "change-me", "DJANGO_DEBUG": "True"}

        self.assertEqual(load_environment(env), "dsv")

    def test_prd_accepts_real_values(self):
        self.assertEqual(load_environment(VALID_PRD), "prd")

    def test_prd_refuses_unsafe_values(self):
        cases = [
            ("DJANGO_SECRET_KEY", ""),
            ("DJANGO_SECRET_KEY", "change-me"),
            ("DJANGO_SECRET_KEY", "unsafe-dev-secret-key"),
            ("DJANGO_DEBUG", "True"),
            ("DJANGO_ALLOWED_HOSTS", ""),
            ("DJANGO_ALLOWED_HOSTS", "api.tagarela.test,localhost"),
            ("DJANGO_ALLOWED_HOSTS", "*"),
            ("DJANGO_ALLOWED_HOSTS", "api.tagarela.invalid"),
            ("POSTGRES_PASSWORD", ""),
            ("POSTGRES_PASSWORD", "tagarela"),
            ("GEMINI_API_KEY", ""),
            ("EMAIL_BACKEND", ""),
            ("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"),
            ("EMAIL_HOST", ""),
            ("EMAIL_HOST", "mailpit"),
            ("EMAIL_HOST", "smtp.tagarela.invalid"),
            ("DEFAULT_FROM_EMAIL", ""),
            ("DEFAULT_FROM_EMAIL", "Tagarela <nao-responda@localhost>"),
            ("DEFAULT_FROM_EMAIL", "Tagarela <nao-responda@tagarela.invalid>"),
        ]
        for name, value in cases:
            with (
                self.subTest(name=name, value=value),
                self.assertRaisesRegex(ImproperlyConfigured, name),
            ):
                load_environment({**VALID_PRD, name: value})


@patch("config.health.connections")
class HealthViewTests(APISimpleTestCase):
    def test_open_without_login(self, connections):
        response = self.client.get("/health", headers={"Authorization": "Bearer invalido"})

        self.assertEqual(response.status_code, 200)

    def test_database_up_returns_200(self, connections):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "checks": {"database": True}})

    def test_database_down_returns_503(self, connections):
        connections["default"].ensure_connection.side_effect = OperationalError("down")

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unhealthy", "checks": {"database": False}})
