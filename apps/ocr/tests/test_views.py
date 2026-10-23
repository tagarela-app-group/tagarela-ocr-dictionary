from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APISimpleTestCase

from apps.ocr.tests.images import uploaded_image

URL = "/api/v1/images/analyze"
RESULT = {
    "ocr": {"text": "The fox"},
    "words": [{"word": "fox", "definitions": ["A canine."], "source": "dictionary"}],
}


@patch("apps.ocr.views.ImageAnalysisService")
class AnalyzeImageViewTests(APISimpleTestCase):
    def setUp(self):
        self.client.force_authenticate(get_user_model()(email="ana@example.com"))

    def test_without_login_returns_401(self, service_class):
        response = self.client_class().post(URL, {"file": uploaded_image()}, format="multipart")

        self.assertEqual(response.status_code, 401)
        service_class.assert_not_called()

    def test_valid_image_returns_analysis(self, service_class):
        service_class.return_value.analyze.return_value = RESULT

        response = self.client.post(URL, {"file": uploaded_image()}, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), RESULT)
        uploaded = service_class.return_value.analyze.call_args.args[0]
        self.assertEqual(uploaded.name, "foto.png")

    def test_missing_file_returns_400(self, service_class):
        response = self.client.post(URL, {}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.json())
        service_class.assert_not_called()

    def test_file_that_is_not_an_image_returns_400(self, service_class):
        file = SimpleUploadedFile("foto.png", b"not an image", content_type="image/png")

        response = self.client.post(URL, {"file": file}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.json())
        service_class.assert_not_called()

    def test_format_outside_allowed_returns_400_with_message(self, service_class):
        file = uploaded_image("GIF", "image/gif", "foto.gif")

        response = self.client.post(URL, {"file": file}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"file": ["Formato inválido. Envie uma imagem JPEG, PNG ou WEBP."]},
        )
        service_class.assert_not_called()

    def test_get_not_allowed(self, service_class):
        response = self.client.get(URL)

        self.assertEqual(response.status_code, 405)
