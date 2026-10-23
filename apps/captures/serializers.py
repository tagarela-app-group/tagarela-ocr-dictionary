from django.conf import settings
from rest_framework import serializers

from apps.captures.models import Capture, CaptureTerm
from apps.common.serializers import StrictSerializer
from apps.ocr.validators import validate_uploaded_image
from apps.transcription.validators import validate_uploaded_audio


class CaptureListParamsSerializer(StrictSerializer):
    updated_since = serializers.DateTimeField(required=False)
    cursor = serializers.CharField(required=False)


class CaptureCreateSerializer(StrictSerializer):
    id = serializers.UUIDField()
    source = serializers.ChoiceField(choices=Capture.Source.choices)
    captured_at = serializers.DateTimeField()
    text = serializers.CharField(required=False, max_length=settings.CAPTURE_MAX_TEXT_LENGTH)

    def validate(self, attrs):
        is_text = attrs["source"] == Capture.Source.TEXT
        if is_text and "text" not in attrs:
            raise serializers.ValidationError({"text": ["Escreva o texto da captura."]})
        if not is_text and "text" in attrs:
            raise serializers.ValidationError(
                {"text": ["Foto e áudio não levam texto. Envie o arquivo."]}
            )

        return attrs


class CaptureFileSerializer(StrictSerializer):
    file = serializers.FileField()

    def validate_file(self, file):
        source = self.context["capture"].source
        if source == Capture.Source.TEXT:
            raise serializers.ValidationError("Captura de texto não recebe arquivo.")
        if source == Capture.Source.AUDIO:
            validate_uploaded_audio(file)
        else:
            validate_uploaded_image(file)

        return file


class TermSerializer(StrictSerializer):
    text = serializers.CharField(max_length=settings.CAPTURE_MAX_TERM_LENGTH)
    start = serializers.IntegerField(min_value=0)
    end = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if attrs["end"] <= attrs["start"]:
            raise serializers.ValidationError({"end": ["O fim do termo vem depois do início."]})

        return attrs


class CaptureUpdateSerializer(StrictSerializer):
    text = serializers.CharField(required=False, max_length=settings.CAPTURE_MAX_TEXT_LENGTH)
    terms = TermSerializer(many=True, required=False, max_length=settings.CAPTURE_MAX_TERMS)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Envie o texto, os termos ou os dois.")

        terms = attrs.get("terms")
        if terms is None:
            return attrs

        text = attrs.get("text", self.instance.text)
        spans = set()
        for index, term in enumerate(terms, start=1):
            span = (term["start"], term["end"])
            if text[term["start"] : term["end"]] != term["text"]:
                raise serializers.ValidationError(
                    {"terms": [f"O termo {index} não bate com o trecho do texto."]}
                )
            if span in spans:
                raise serializers.ValidationError({"terms": [f"O termo {index} está repetido."]})
            spans.add(span)

        return attrs


class CaptureTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaptureTerm
        fields = ("text", "start", "end")


class CaptureSerializer(serializers.ModelSerializer):
    terms = CaptureTermSerializer(many=True, read_only=True)

    class Meta:
        model = Capture
        fields = (
            "id",
            "source",
            "status",
            "text",
            "original_text",
            "terms",
            "error",
            "captured_at",
            "processed_at",
            "analyzed_at",
            "discarded_at",
            "created_at",
            "updated_at",
        )
