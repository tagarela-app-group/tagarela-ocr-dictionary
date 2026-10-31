from collections.abc import Mapping

from rest_framework import serializers

FORMALITY_LEVELS = ("slang", "informal", "neutral", "formal")
DIALOGUE_SPEAKERS = ("A", "B")


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


class UsageExampleSerializer(LanguageAnalysisStrictSerializer):
    original = serializers.CharField(allow_blank=False)
    translation = serializers.CharField(allow_blank=False)


class UsageContextSerializer(LanguageAnalysisStrictSerializer):
    context = serializers.CharField(allow_blank=False)
    fits = serializers.BooleanField()
    alternative = serializers.CharField(allow_null=True, allow_blank=False)


class DialogueLineSerializer(LanguageAnalysisStrictSerializer):
    speaker = serializers.ChoiceField(choices=DIALOGUE_SPEAKERS)
    text = serializers.CharField(allow_blank=False)
    translation = serializers.CharField(allow_blank=False)


def word_list(max_length: int) -> serializers.ListField:
    return serializers.ListField(
        child=serializers.CharField(allow_blank=False), max_length=max_length, allow_empty=True
    )


class LinguisticAnalysisSerializer(LanguageAnalysisStrictSerializer):
    translation = serializers.CharField(allow_null=True, allow_blank=False)
    meaning_in_context = serializers.CharField(allow_null=True, allow_blank=False)
    explanation = serializers.CharField(allow_blank=False)
    examples = UsageExampleSerializer(many=True, max_length=3)
    phonetic = serializers.CharField(allow_null=True, allow_blank=False)
    source_definition = serializers.CharField(allow_null=True, allow_blank=False)
    source_meaning_in_context = serializers.CharField(allow_null=True, allow_blank=False)
    source_explanation = serializers.CharField(allow_blank=False)
    pitfall = serializers.CharField(allow_null=True, allow_blank=False)
    literal = serializers.CharField(allow_null=True, allow_blank=False)
    imagine = serializers.CharField(allow_null=True, allow_blank=False)
    source_pitfall_wrong = serializers.CharField(allow_null=True, allow_blank=False)
    source_pitfall_right = serializers.CharField(allow_null=True, allow_blank=False)
    collocations = word_list(6)
    synonyms = word_list(5)
    antonyms = word_list(5)
    formality = serializers.ChoiceField(choices=FORMALITY_LEVELS)
    formality_note = serializers.CharField(allow_null=True, allow_blank=False)
    contexts = UsageContextSerializer(many=True, max_length=4)
    dialogue = DialogueLineSerializer(many=True, max_length=4)
