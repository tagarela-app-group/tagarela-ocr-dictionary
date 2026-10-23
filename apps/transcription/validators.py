from django.conf import settings
from rest_framework import serializers

from apps.transcription.audio import InvalidAudioError, read_audio_info

DURATION_TOLERANCE_SECONDS = 1
INVALID_FORMAT = "Formato inválido. Envie um áudio M4A (AAC)."


def validate_uploaded_audio(file) -> None:
    if file.size > settings.TRANSCRIPTION_MAX_AUDIO_SIZE_BYTES:
        max_mb = settings.TRANSCRIPTION_MAX_AUDIO_SIZE_BYTES // (1024 * 1024)
        raise serializers.ValidationError(f"O áudio deve ter no máximo {max_mb} MB.")

    if file.content_type not in settings.TRANSCRIPTION_ALLOWED_CONTENT_TYPES:
        raise serializers.ValidationError(INVALID_FORMAT)

    try:
        info = read_audio_info(file)
    except InvalidAudioError:
        raise serializers.ValidationError("O arquivo enviado não é um áudio válido.")
    finally:
        file.seek(0)

    if "m4a" not in info.formats or info.codecs != ("aac",):
        raise serializers.ValidationError(INVALID_FORMAT)

    max_seconds = settings.TRANSCRIPTION_MAX_AUDIO_SECONDS
    if info.seconds is None or info.seconds > max_seconds + DURATION_TOLERANCE_SECONDS:
        raise serializers.ValidationError(f"O áudio deve ter no máximo {max_seconds} segundos.")
