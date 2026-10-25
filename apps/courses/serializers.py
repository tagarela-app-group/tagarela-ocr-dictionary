from rest_framework import serializers

from apps.common.serializers import StrictSerializer
from apps.courses.models import Course

LANGUAGE_ERRORS = {
    "required": "Escolha um idioma.",
    "invalid_choice": "Escolha um idioma da lista.",
}


class CourseInputSerializer(StrictSerializer):
    learning = serializers.ChoiceField(
        choices=Course.Language.choices, error_messages=LANGUAGE_ERRORS
    )
    base = serializers.ChoiceField(choices=Course.Language.choices, error_messages=LANGUAGE_ERRORS)

    def validate(self, attrs):
        if attrs["learning"] == attrs["base"]:
            raise serializers.ValidationError(
                {"base": ["Escolha um idioma diferente do que você quer aprender."]}
            )

        return attrs


class CourseSerializer(serializers.ModelSerializer):
    terms = serializers.IntegerField(source="term_count", read_only=True)

    class Meta:
        model = Course
        fields = ("id", "learning", "base", "active", "terms")
