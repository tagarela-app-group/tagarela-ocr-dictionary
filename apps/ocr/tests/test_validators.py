from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from rest_framework import serializers

from apps.ocr.tests.images import uploaded_image
from apps.ocr.validators import validate_uploaded_image

INVALID_FORMAT = "Formato inválido. Envie uma imagem JPEG, PNG ou WEBP."


class ValidateUploadedImageTests(SimpleTestCase):
    def assert_invalid(self, file, message: str) -> None:
        with self.assertRaises(serializers.ValidationError) as context:
            validate_uploaded_image(file)

        self.assertEqual(context.exception.detail, [message])

    def test_accepts_jpeg_png_webp_and_rewinds_file(self):
        for image_format, content_type in [
            ("JPEG", "image/jpeg"),
            ("PNG", "image/png"),
            ("WEBP", "image/webp"),
        ]:
            with self.subTest(image_format):
                file = uploaded_image(image_format, content_type)

                validate_uploaded_image(file)

                self.assertEqual(file.tell(), 0)

    @override_settings(OCR_MAX_IMAGE_SIZE_BYTES=10)
    def test_rejects_file_over_size_limit(self):
        self.assert_invalid(uploaded_image(), "A imagem deve ter no máximo 10 MB.")

    def test_rejects_content_type_outside_allowed(self):
        self.assert_invalid(uploaded_image("GIF", "image/gif", "foto.gif"), INVALID_FORMAT)

    def test_rejects_file_that_is_not_an_image(self):
        file = SimpleUploadedFile("foto.png", b"not an image", content_type="image/png")

        self.assert_invalid(file, "O arquivo enviado não é uma imagem válida.")
        self.assertEqual(file.tell(), 0)

    def test_rejects_real_format_outside_allowed_even_with_allowed_content_type(self):
        self.assert_invalid(uploaded_image("GIF", "image/png", "foto.png"), INVALID_FORMAT)
