from django.conf import settings
from rest_framework import serializers

from apps.common.serializers import StrictSerializer
from apps.vocabulary.models import Group, Term
from apps.vocabulary.services import clean_text


class GroupCreateSerializer(StrictSerializer):
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


class MoveTermsSerializer(StrictSerializer):
    terms = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        error_messages={"empty": "Escolha pelo menos um termo."},
    )
    group = serializers.UUIDField(allow_null=True)


class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = ("id", "text", "translation", "kind", "level")


class GroupSerializer(serializers.ModelSerializer):
    terms = TermSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ("id", "name", "icon", "accent", "terms")


class VocabularySerializer(serializers.Serializer):
    groups = GroupSerializer(many=True)
    ungrouped = TermSerializer(many=True)
