from PIL import Image, UnidentifiedImageError
from django.conf import settings
from rest_framework import serializers


def validate_uploaded_image(file) -> None:
    if file.size > settings.OCR_MAX_IMAGE_SIZE_BYTES:
        raise serializers.ValidationError("A imagem deve ter no máximo 10 MB.")

    if file.content_type not in settings.OCR_ALLOWED_CONTENT_TYPES:
        raise serializers.ValidationError("Formato inválido. Envie uma imagem JPEG, PNG ou WEBP.")

    try:
        image = Image.open(file)
        image.verify()
    except (UnidentifiedImageError, OSError):
        raise serializers.ValidationError("O arquivo enviado não é uma imagem válida.")
    finally:
        file.seek(0)

    if image.format not in settings.OCR_ALLOWED_FORMATS:
        raise serializers.ValidationError("Formato inválido. Envie uma imagem JPEG, PNG ou WEBP.")
