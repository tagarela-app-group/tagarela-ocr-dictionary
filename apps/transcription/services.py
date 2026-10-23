from pathlib import Path

from apps.transcription.providers.whisper import WhisperProvider


class TranscriptionService:
    def __init__(self, provider: WhisperProvider | None = None) -> None:
        self.provider = provider or WhisperProvider()

    def transcribe(self, audio_path: Path) -> str:
        return self.provider.transcribe_path(audio_path)
