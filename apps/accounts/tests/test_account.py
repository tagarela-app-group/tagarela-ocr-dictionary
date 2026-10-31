from rest_framework.test import APITestCase

from apps.accounts.tests.test_auth_flows import PASSWORD, AuthFlowTestCase
from apps.captures.tests.helpers import make_user

ACCOUNT = "/api/v1/account"


class AccountTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)

    def patch(self, data):
        return self.client.patch(ACCOUNT, data, format="json")

    def test_sets_country_and_returns_user(self):
        response = self.patch({"country": "BR"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["country"], "BR")
        self.assertEqual(response.json()["email"], "ana@example.com")
        self.user.refresh_from_db()
        self.assertEqual(self.user.country, "BR")

    def test_blank_country_clears_it(self):
        self.user.country = "AR"
        self.user.save()

        response = self.patch({"country": ""})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("country", response.json())
        self.user.refresh_from_db()
        self.assertEqual(self.user.country, "")

    def test_unknown_country_is_rejected(self):
        for code in ["ZZ", "br", "BRA", "EU"]:
            with self.subTest(code):
                response = self.patch({"country": code})

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"country": ["Escolha um país da lista."]})

    def test_missing_country_is_rejected(self):
        response = self.patch({})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"country": ["Escolha um país."]})


class SessionCountryTests(AuthFlowTestCase):
    def test_session_user_includes_country(self):
        user = self.create_verified_user()
        user.country = "PT"
        user.save()

        response = self.post("/auth/login", {"email": "ana@example.com", "password": PASSWORD})

        self.assertEqual(response.json()["data"]["user"]["country"], "PT")
