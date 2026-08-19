from rest_framework import serializers

from apps.ocr.validators import validate_uploaded_image


class ImageAnalyzeSerializer(serializers.Serializer):
    file = serializers.ImageField(validators=[validate_uploaded_image])
