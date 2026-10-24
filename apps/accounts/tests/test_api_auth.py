from apps.accounts.tests.test_auth_flows import PASSWORD, AuthFlowTestCase

PROTECTED = "/api/v1/captures"


class ApiRouteAuthTests(AuthFlowTestCase):
    def access_token(self) -> str:
        self.create_verified_user()
        response = self.post("/auth/login", {"email": "ana@example.com", "password": PASSWORD})

        return response.json()["meta"]["access_token"]

    def call(self, authorization: str | None = None):
        headers = {"Authorization": authorization} if authorization else {}
        return self.client.get(PROTECTED, headers=headers)

    def test_without_token_returns_401(self):
        response = self.call()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_invalid_token_returns_401(self):
        response = self.call("Bearer token-invalido")

        self.assertEqual(response.status_code, 401)

    def test_login_access_token_reaches_the_view(self):
        response = self.call(f"Bearer {self.access_token()}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])
