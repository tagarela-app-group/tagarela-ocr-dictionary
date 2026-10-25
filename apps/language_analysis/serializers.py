import re
from collections.abc import Mapping

from django.conf import settings
from rest_framework import serializers

LANGUAGE_CODE_PATTERN = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z]{2,4})?$")
CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
FORMALITY_LEVELS = ("slang", "informal", "neutral", "formal")


class LanguageAnalysisStrictSerializer(serializers.Serializer):
    def to_internal_value(self, data: object) -> dict:
        unknown = {}
        if isinstance(data, Mapping):
            unknown = {field: ["Unknown field."] for field in sorted(set(data) - set(self.fields))}

        try:
            value = super().to_internal_value(data)
        except serializers.ValidationError as error:
            if unknown and isinstance(error.detail, dict):
                raise serializers.ValidationError({**error.detail, **unknown}) from error
            raise

        if unknown:
            raise serializers.ValidationError(unknown)

        return value


class LanguageAnalysisRequestSerializer(LanguageAnalysisStrictSerializer):
    text = serializers.CharField(
        max_length=settings.LANGUAGE_ANALYSIS_MAX_TEXT_LENGTH,
        trim_whitespace=True,
        error_messages={
            "required": "Text is required.",
            "blank": "Text must not be empty.",
            "max_length": "Text must not exceed {max_length} characters.",
        },
    )
    selected_term = serializers.CharField(required=False, allow_null=True, allow_blank=False)
    source_language = serializers.CharField(required=False, default="auto")
    target_language = serializers.CharField(required=False, default="pt-BR")
    level = serializers.ChoiceField(
        choices=CEFR_LEVELS,
        required=False,
        allow_null=True,
        default=None,
        error_messages={"invalid_choice": "Level must be one of: A1, A2, B1, B2, C1, C2."},
    )

    def validate_selected_term(self, value: str | None) -> str | None:
        if value is None:
            return None

        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Selected term must not be empty.")
        return value

    def validate_source_language(self, value: str) -> str:
        if value == "auto":
            return value
        return self._validate_language_code(value, "Source language", allow_auto=True)

    def validate_target_language(self, value: str) -> str:
        return self._validate_language_code(value, "Target language", allow_auto=False)

    def _validate_language_code(self, value: str, field_name: str, allow_auto: bool) -> str:
        if not LANGUAGE_CODE_PATTERN.fullmatch(value):
            accepted = "a language code or 'auto'" if allow_auto else "a language code"
            raise serializers.ValidationError(f"{field_name} must be {accepted}.")
        return value


class AlternativeMeaningSerializer(LanguageAnalysisStrictSerializer):
    meaning = serializers.CharField(allow_blank=False)
    usage_context = serializers.CharField(allow_blank=False)
    example = serializers.CharField(allow_blank=False)
    translation = serializers.CharField(allow_blank=False)


class UsageExampleSerializer(LanguageAnalysisStrictSerializer):
    original = serializers.CharField(allow_blank=False)
    translation = serializers.CharField(allow_blank=False)
    usage_context = serializers.CharField(allow_blank=False)


class UsageContextSerializer(LanguageAnalysisStrictSerializer):
    context = serializers.CharField(allow_blank=False)
    fits = serializers.BooleanField()
    alternative = serializers.CharField(allow_null=True, allow_blank=False)


def word_list(max_length: int) -> serializers.ListField:
    return serializers.ListField(
        child=serializers.CharField(allow_blank=False), max_length=max_length, allow_empty=True
    )


class LinguisticAnalysisSerializer(LanguageAnalysisStrictSerializer):
    focus = serializers.CharField(allow_blank=False)
    detected_language = serializers.CharField(allow_blank=False)
    translation = serializers.CharField(allow_null=True, allow_blank=False)
    meaning_in_context = serializers.CharField(allow_null=True, allow_blank=False)
    explanation = serializers.CharField(allow_blank=False)
    part_of_speech = serializers.CharField(allow_null=True, allow_blank=False)
    is_ambiguous = serializers.BooleanField()
    alternative_meanings = AlternativeMeaningSerializer(many=True, max_length=3)
    examples = UsageExampleSerializer(many=True, max_length=3)
    usage_notes = word_list(5)
    phonetic = serializers.CharField(allow_null=True, allow_blank=False)
    source_definition = serializers.CharField(allow_null=True, allow_blank=False)
    source_meaning_in_context = serializers.CharField(allow_null=True, allow_blank=False)
    source_explanation = serializers.CharField(allow_blank=False)
    pitfall = serializers.CharField(allow_null=True, allow_blank=False)
    collocations = word_list(6)
    synonyms = word_list(5)
    antonyms = word_list(5)
    formality = serializers.ChoiceField(choices=FORMALITY_LEVELS)
    formality_note = serializers.CharField(allow_null=True, allow_blank=False)
    contexts = UsageContextSerializer(many=True, max_length=4)


class LanguageAnalysisMetadataSerializer(LanguageAnalysisStrictSerializer):
    model = serializers.CharField(allow_blank=False)
    prompt_version = serializers.CharField(allow_blank=False)


class LanguageAnalysisResponseSerializer(LanguageAnalysisStrictSerializer):
    input = LanguageAnalysisRequestSerializer()
    analysis = LinguisticAnalysisSerializer()
    metadata = LanguageAnalysisMetadataSerializer()
