from django.conf import settings
from rest_framework import serializers

from apps.common.serializers import StrictSerializer
from apps.common.text import clean_text
from apps.vocabulary.models import Group, Term


class GroupInputSerializer(StrictSerializer):
    name = serializers.CharField(
        max_length=settings.VOCABULARY_GROUP_NAME_MAX_LENGTH,
        error_messages={
            "required": "Dê um nome ao grupo.",
            "blank": "Dê um nome ao grupo.",
            "max_length": "O nome do grupo tem até {max_length} caracteres.",
        },
    )
    icon = serializers.RegexField(r"^[a-z][a-z0-9_]*$", max_length=30)
    accent = serializers.ChoiceField(choices=Group.Accent.choices)

    def validate_name(self, value: str) -> str:
        return clean_text(value)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Envie o nome, o ícone ou a cor.")

        return attrs


class TermsSerializer(StrictSerializer):
    terms = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        error_messages={"empty": "Escolha pelo menos um termo."},
    )


class MoveTermsSerializer(TermsSerializer):
    group = serializers.UUIDField(allow_null=True)


class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = (
            "id",
            "text",
            "translation",
            "kind",
            "level",
            "interval_days",
            "due_at",
            "created_at",
        )


class GroupSerializer(serializers.ModelSerializer):
    terms = TermSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ("id", "name", "icon", "accent", "terms")


class VocabularySerializer(serializers.Serializer):
    groups = GroupSerializer(many=True)
    ungrouped = TermSerializer(many=True)
