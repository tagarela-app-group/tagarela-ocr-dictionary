import re
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts.models import User

BASE = "/api/auth/app/v1"
PASSWORD = "s3nha-forte-123"
GOOGLE_CLIENT_ID = "google-web.apps.googleusercontent.com"
APPLE_CLIENT_ID = "app.tagarela.ios"


class AuthFlowTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def post(self, path: str, data: dict, session_token: str | None = None):
        headers = {"X-Session-Token": session_token} if session_token else {}
        return self.client.post(
            f"{BASE}{path}", data, content_type="application/json", headers=headers
        )

    def last_code(self) -> str:
        return re.search(r"\b\d{6}\b", mail.outbox[-1].body).group()

    def last_html(self) -> str:
        return next(
            content for content, mimetype in mail.outbox[-1].alternatives if mimetype == "text/html"
        )

    def pending_flow(self, response) -> str:
        return next(
            flow["id"] for flow in response.json()["data"]["flows"] if flow.get("is_pending")
        )

    def create_verified_user(self, email: str = "ana@example.com") -> User:
        user = User.objects.create_user(email, PASSWORD, name="Ana")
        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)

        return user


class SignupTests(AuthFlowTestCase):
    def signup(self, **data):
        payload = {"email": "ana@example.com", "password": PASSWORD, "name": "Ana Souza"}
        return self.post("/auth/signup", {**payload, **data})

    def test_signup_requires_email_code_then_returns_tokens(self):
        response = self.signup()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.pending_flow(response), "verify_email")
        session_token = response.json()["meta"]["session_token"]

        response = self.post("/auth/email/verify", {"key": self.last_code()}, session_token)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["user"]["display"], "Ana Souza")
        self.assertIn("access_token", body["meta"])
        self.assertIn("refresh_token", body["meta"])
        self.assertTrue(EmailAddress.objects.get(email="ana@example.com").verified)

    def test_code_is_six_digits_and_sent_to_email(self):
        self.signup()

        self.assertEqual(mail.outbox[-1].to, ["ana@example.com"])
        self.assertRegex(self.last_code(), r"^\d{6}$")
        self.assertEqual(mail.outbox[-1].subject, "[Tagarela] Confirme seu e-mail")
        self.assertNotIn("navegador", mail.outbox[-1].body)

    def test_code_email_has_html_version_with_code_and_validity(self):
        self.signup()

        html = self.last_html()
        self.assertIn(self.last_code(), html)
        self.assertIn("Confirme seu e-mail", html)
        self.assertIn("O código vale 15 minutos.", html)
        self.assertIn("O código vale 15 minutos.", mail.outbox[-1].body)
        self.assertNotIn("<a ", html)

    @override_settings(AUTH_CODE_TTL_SECONDS=600)
    def test_code_validity_follows_setting(self):
        self.signup()

        self.assertIn("O código vale 10 minutos.", self.last_html())

    def test_wrong_code_is_rejected(self):
        session_token = self.signup().json()["meta"]["session_token"]
        wrong = "000000" if self.last_code() != "000000" else "111111"

        response = self.post("/auth/email/verify", {"key": wrong}, session_token)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(EmailAddress.objects.get(email="ana@example.com").verified)

    def test_signup_saves_name_and_lowercase_email(self):
        self.signup(email="Ana@Example.com")

        self.assertEqual(User.objects.get().email, "ana@example.com")
        self.assertEqual(User.objects.get().name, "Ana Souza")

    def test_signup_with_existing_email_does_not_reveal_account(self):
        self.create_verified_user()

        response = self.signup()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.pending_flow(response), "verify_email")
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(mail.outbox[-1].subject, "[Tagarela] Você já tem conta no Tagarela")
        self.assertIn("Esqueci minha senha", mail.outbox[-1].body)
        self.assertNotIn("http", mail.outbox[-1].body)
        self.assertIn("ana@example.com", self.last_html())
        self.assertIn("Esqueci minha senha", self.last_html())
        self.assertNotIn("<a ", self.last_html())

    def test_signup_rejects_missing_name_and_weak_password(self):
        for data, param in [({"name": ""}, "name"), ({"password": "123"}, "password")]:
            with self.subTest(param):
                response = self.signup(**data)

                self.assertEqual(response.status_code, 400)
                params = {error.get("param") for error in response.json()["errors"]}
                self.assertIn(param, params)


class LoginTests(AuthFlowTestCase):
    def login(self, password: str = PASSWORD):
        return self.post("/auth/login", {"email": "ana@example.com", "password": password})

    def test_verified_user_gets_tokens(self):
        self.create_verified_user()

        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json()["meta"])

    def test_wrong_password_returns_400(self):
        self.create_verified_user()

        self.assertEqual(self.login("senha-errada-999").status_code, 400)

    def test_unverified_email_must_verify_first(self):
        User.objects.create_user("ana@example.com", PASSWORD, name="Ana")
        EmailAddress.objects.create(
            user=User.objects.get(), email="ana@example.com", verified=False, primary=True
        )

        response = self.login()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.pending_flow(response), "verify_email")

    def test_access_token_authenticates_and_refresh_rotates(self):
        self.create_verified_user()
        tokens = self.login().json()["meta"]

        session = self.client.get(
            f"{BASE}/auth/session", headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        refreshed = self.post("/tokens/refresh", {"refresh_token": tokens["refresh_token"]})

        self.assertEqual(session.status_code, 200)
        self.assertEqual(session.json()["data"]["user"]["email"], "ana@example.com")
        self.assertEqual(refreshed.status_code, 200)
        self.assertNotEqual(refreshed.json()["data"]["refresh_token"], tokens["refresh_token"])

    def test_logout_invalidates_refresh_token(self):
        self.create_verified_user()
        tokens = self.login().json()["meta"]

        logout = self.client.delete(
            f"{BASE}/auth/session", headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        refreshed = self.post("/tokens/refresh", {"refresh_token": tokens["refresh_token"]})

        self.assertEqual(logout.status_code, 401)
        self.assertEqual(refreshed.status_code, 400)


class PasswordResetTests(AuthFlowTestCase):
    def test_reset_by_code_changes_password_and_logs_in(self):
        user = self.create_verified_user()

        response = self.post("/auth/password/request", {"email": "ana@example.com"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.pending_flow(response), "password_reset_by_code")
        session_token = response.json()["meta"]["session_token"]
        code = self.last_code()

        check = self.client.get(
            f"{BASE}/auth/password/reset",
            headers={"X-Session-Token": session_token, "X-Password-Reset-Key": code},
        )
        response = self.post(
            "/auth/password/reset", {"key": code, "password": "nova-s3nha-456"}, session_token
        )

        self.assertEqual(check.status_code, 200)
        self.assertEqual(mail.outbox[0].subject, "[Tagarela] Código pra nova senha")
        self.assertIn(code, self.last_html())
        self.assertIn("Crie uma nova senha", self.last_html())
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json()["meta"])
        user.refresh_from_db()
        self.assertTrue(user.check_password("nova-s3nha-456"))

    def test_unknown_email_does_not_reveal_account(self):
        response = self.post("/auth/password/request", {"email": "ninguem@example.com"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.pending_flow(response), "password_reset_by_code")
        self.assertEqual(mail.outbox, [])


@override_settings(
    SOCIALACCOUNT_PROVIDERS={
        "google": {"APPS": [{"client_id": GOOGLE_CLIENT_ID, "secret": ""}]},
        "apple": {"APPS": [{"client_id": APPLE_CLIENT_ID, "secret": ""}]},
    }
)
class SocialLoginTests(AuthFlowTestCase):
    def provider_login(self, provider: str, client_id: str):
        token = {"client_id": client_id, "id_token": "id-token-do-app"}
        return self.post(
            "/auth/provider/token", {"provider": provider, "process": "login", "token": token}
        )

    @patch("allauth.socialaccount.providers.google.views._verify_and_decode")
    def test_google_creates_verified_user_with_name(self, verify):
        verify.return_value = {
            "sub": "google-123",
            "email": "bia@gmail.com",
            "email_verified": True,
            "given_name": "Bia",
            "family_name": "Lima",
        }

        response = self.provider_login("google", GOOGLE_CLIENT_ID)

        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json()["meta"])
        user = User.objects.get(email="bia@gmail.com")
        self.assertEqual(user.name, "Bia Lima")
        self.assertFalse(user.has_usable_password())
        self.assertTrue(EmailAddress.objects.get(email="bia@gmail.com").verified)

    @patch("allauth.socialaccount.providers.google.views._verify_and_decode")
    def test_google_with_existing_email_logs_into_same_account(self, verify):
        user = self.create_verified_user("bia@gmail.com")
        verify.return_value = {
            "sub": "google-123",
            "email": "bia@gmail.com",
            "email_verified": True,
        }

        response = self.provider_login("google", GOOGLE_CLIENT_ID)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertTrue(user.socialaccount_set.filter(provider="google").exists())

    @patch(
        "allauth.socialaccount.providers.apple.views.AppleOAuth2Adapter.get_verified_identity_data"
    )
    def test_apple_creates_user_without_name(self, verify):
        verify.return_value = {
            "sub": "apple-001",
            "email": "x1@privaterelay.appleid.com",
            "email_verified": "true",
        }

        response = self.provider_login("apple", APPLE_CLIENT_ID)

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email="x1@privaterelay.appleid.com")
        self.assertEqual(user.name, "")

    def test_invalid_token_is_rejected(self):
        response = self.provider_login("google", GOOGLE_CLIENT_ID)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())
