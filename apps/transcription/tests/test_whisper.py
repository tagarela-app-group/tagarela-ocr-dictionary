from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.transcription.providers.whisper import WhisperProvider


class FakeModel:
    def __init__(self, texts: list[str]) -> None:
        self.texts = texts
        self.calls = []

    def transcribe(self, path: str, **options):
        self.calls.append((path, options))
        segments = (SimpleNamespace(text=text) for text in self.texts)

        return segments, SimpleNamespace(duration=1.0)


@override_settings(
    TRANSCRIPTION_MODEL="base.en",
    TRANSCRIPTION_COMPUTE_TYPE="int8",
    TRANSCRIPTION_CPU_THREADS=0,
    TRANSCRIPTION_BEAM_SIZE=5,
    TRANSCRIPTION_MODEL_DIR=Path("/models"),
)
class WhisperProviderTests(SimpleTestCase):
    def setUp(self):
        patcher = patch.object(WhisperProvider, "_models", {})
        self.models = patcher.start()
        self.addCleanup(patcher.stop)

    def test_joins_segments_ignoring_blank(self):
        model = FakeModel([" Mind the gap", "  ", " between the train."])
        self.models[("base.en", "int8", 0)] = model

        text = WhisperProvider().transcribe_path(Path("audio.m4a"))

        self.assertEqual(text, "Mind the gap between the train.")
        self.assertEqual(
            model.calls,
            [("audio.m4a", {"language": "en", "beam_size": 5, "vad_filter": True})],
        )

    def test_overrides_win_over_settings(self):
        provider = WhisperProvider("tiny.en", "float32", 2, 1)

        self.assertEqual(
            (provider.model_name, provider.compute_type, provider.cpu_threads, provider.beam_size),
            ("tiny.en", "float32", 2, 1),
        )

    def test_loads_each_model_once(self):
        with patch("faster_whisper.WhisperModel") as whisper_model:
            WhisperProvider().load()
            WhisperProvider().load()
            WhisperProvider(model_name="tiny.en").load()

        self.assertEqual(whisper_model.call_count, 2)
        whisper_model.assert_any_call(
            "base.en", device="cpu", compute_type="int8", cpu_threads=0, download_root="/models"
        )
        whisper_model.assert_any_call(
            "tiny.en", device="cpu", compute_type="int8", cpu_threads=0, download_root="/models"
        )
