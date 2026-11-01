from rest_framework import serializers

from apps.common.serializers import StrictSerializer
from apps.daily_words.models import DailyWord
from apps.vocabulary.serializers import TermSerializer


class GeneratedWordSerializer(StrictSerializer):
    source_word = serializers.CharField(allow_blank=False, max_length=255)
    phonetic = serializers.CharField(allow_null=True, allow_blank=False, max_length=255)
    source_example = serializers.CharField(allow_blank=False)
    target_meaning = serializers.CharField(allow_blank=False)


class DailyWordSerializer(serializers.ModelSerializer):
    term = TermSerializer(allow_null=True)

    class Meta:
        model = DailyWord
        fields = ("text", "kind", "phonetic", "example", "meaning", "term")
