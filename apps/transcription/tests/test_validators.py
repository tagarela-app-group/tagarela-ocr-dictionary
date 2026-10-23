from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from rest_framework import serializers

from apps.transcription.tests.audio import uploaded_audio
from apps.transcription.validators import validate_uploaded_audio

INVALID_FORMAT = "Formato inválido. Envie um áudio M4A (AAC)."


class ValidateUploadedAudioTests(SimpleTestCase):
    def assert_invalid(self, file, message: str) -> None:
        with self.assertRaises(serializers.ValidationError) as context:
            validate_uploaded_audio(file)

        self.assertEqual(context.exception.detail, [message])

    def test_accepts_m4a_aac_and_rewinds_file(self):
        for content_type in ["audio/mp4", "audio/m4a", "audio/x-m4a"]:
            with self.subTest(content_type):
                file = uploaded_audio(content_type=content_type)

                validate_uploaded_audio(file)

                self.assertEqual(file.tell(), 0)

    @override_settings(TRANSCRIPTION_MAX_AUDIO_SIZE_BYTES=1024 * 1024)
    def test_rejects_file_over_size_limit(self):
        file = SimpleUploadedFile("audio.m4a", b"0" * (1024 * 1024 + 1), content_type="audio/mp4")

        self.assert_invalid(file, "O áudio deve ter no máximo 1 MB.")

    def test_rejects_content_type_outside_allowed(self):
        self.assert_invalid(uploaded_audio(content_type="audio/wav"), INVALID_FORMAT)

    def test_rejects_file_that_is_not_audio(self):
        file = SimpleUploadedFile("audio.m4a", b"not an audio", content_type="audio/mp4")

        self.assert_invalid(file, "O arquivo enviado não é um áudio válido.")
        self.assertEqual(file.tell(), 0)

    def test_rejects_other_container_or_codec(self):
        for container_format, codec in [("wav", "pcm_s16le"), ("ipod", "alac")]:
            with self.subTest(codec):
                file = uploaded_audio(container_format=container_format, codec=codec)

                self.assert_invalid(file, INVALID_FORMAT)

    @override_settings(TRANSCRIPTION_MAX_AUDIO_SECONDS=2)
    def test_duration_limit_has_one_second_tolerance(self):
        validate_uploaded_audio(uploaded_audio(seconds=2.5))

        self.assert_invalid(uploaded_audio(seconds=4), "O áudio deve ter no máximo 2 segundos.")
