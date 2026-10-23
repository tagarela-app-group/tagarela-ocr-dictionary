import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase

from apps.transcription.tests.audio import audio_bytes


@patch("apps.transcription.management.commands.benchmark_transcription.WhisperProvider")
class BenchmarkTranscriptionTests(SimpleTestCase):
    def test_reports_time_cpu_and_text_per_file(self, provider_class):
        provider = provider_class.return_value
        provider.model_name, provider.compute_type = "tiny.en", "int8"
        provider.beam_size, provider.cpu_threads = 5, 0
        provider.transcribe_path.return_value = "mind the gap"
        output = StringIO()

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "clip.m4a"
            path.write_bytes(audio_bytes(seconds=2))
            call_command("benchmark_transcription", str(path), "--model", "tiny.en", stdout=output)

        provider_class.assert_called_once_with(
            model_name="tiny.en", compute_type=None, cpu_threads=None, beam_size=None
        )
        provider.load.assert_called_once_with()
        provider.transcribe_path.assert_called_once_with(path)
        lines = output.getvalue().splitlines()
        self.assertEqual(lines[0], "modelo tiny.en | int8 | beam 5 | threads auto")
        self.assertRegex(lines[1], r"^carga: ")
        self.assertRegex(lines[2], r"^clip\.m4a: áudio 2\.\d s \| tempo .+ núcleos$")
        self.assertEqual(lines[3], "  mind the gap")
        self.assertRegex(lines[4], r"^memória pico: \d+ MB$")

    def test_missing_file_stops_before_loading_model(self, provider_class):
        with self.assertRaisesMessage(CommandError, "Arquivo não encontrado: nada.m4a"):
            call_command("benchmark_transcription", "nada.m4a")

        provider_class.assert_not_called()
