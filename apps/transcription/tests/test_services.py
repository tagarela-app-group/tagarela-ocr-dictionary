from pathlib import Path
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.transcription.services import TranscriptionService


class TranscriptionServiceTests(SimpleTestCase):
    def test_transcribes_with_provider(self):
        provider = Mock()
        provider.transcribe_path.return_value = "mind the gap"
        path = Path("audio.m4a")

        text = TranscriptionService(provider).transcribe(path)

        self.assertEqual(text, "mind the gap")
        provider.transcribe_path.assert_called_once_with(path)
