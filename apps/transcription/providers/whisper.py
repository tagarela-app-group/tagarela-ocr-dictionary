import threading
from pathlib import Path

from django.conf import settings


class WhisperProvider:
    _models: dict = {}
    _lock = threading.Lock()

    def __init__(
        self,
        model_name: str | None = None,
        compute_type: str | None = None,
        cpu_threads: int | None = None,
        beam_size: int | None = None,
    ) -> None:
        self.model_name = model_name or settings.TRANSCRIPTION_MODEL
        self.compute_type = compute_type or settings.TRANSCRIPTION_COMPUTE_TYPE
        self.cpu_threads = (
            settings.TRANSCRIPTION_CPU_THREADS if cpu_threads is None else cpu_threads
        )
        self.beam_size = beam_size or settings.TRANSCRIPTION_BEAM_SIZE

    def transcribe_path(self, audio_path: Path) -> str:
        segments, _ = self.load().transcribe(
            str(audio_path),
            language="en",
            beam_size=self.beam_size,
            vad_filter=True,
        )

        return " ".join(segment.text.strip() for segment in segments if segment.text.strip())

    def load(self):
        key = (self.model_name, self.compute_type, self.cpu_threads)
        model = self._models.get(key)
        if model is None:
            with self._lock:
                model = self._models.get(key)
                if model is None:
                    from faster_whisper import WhisperModel

                    model = WhisperModel(
                        self.model_name,
                        device="cpu",
                        compute_type=self.compute_type,
                        cpu_threads=self.cpu_threads,
                        download_root=str(settings.TRANSCRIPTION_MODEL_DIR),
                    )
                    self._models[key] = model

        return model
