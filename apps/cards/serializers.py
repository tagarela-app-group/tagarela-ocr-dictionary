from rest_framework import serializers

from apps.captures.models import Capture, CaptureTerm
from apps.common.serializers import StrictSerializer
from apps.vocabulary.models import Group


class RevealSerializer(StrictSerializer):
    revealed = serializers.BooleanField(required=False)
    pitfall_revealed = serializers.BooleanField(required=False)
    formality_revealed = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError({"revealed": ["Informe o que foi revelado."]})

        return attrs


def mistake(analysis: dict) -> dict | None:
    wrong = analysis.get("source_pitfall_wrong")
    right = analysis.get("source_pitfall_right")
    if not wrong or not right:
        return None

    return {"wrong": wrong, "right": right}


def fits(contexts: list[dict]) -> list[dict]:
    return [
        {
            "context": usage["context"],
            "fits": usage["fits"],
            "alternative": usage["alternative"],
        }
        for usage in contexts
    ]


class CardSerializer(serializers.BaseSerializer):
    def to_representation(self, card):
        analysis = card.analysis
        return {
            "phonetic": analysis.get("phonetic"),
            "learning": {
                "definition": analysis.get("source_definition"),
                "in_context": analysis.get("source_meaning_in_context"),
                "explanation": analysis.get("source_explanation"),
            },
            "base": {
                "translation": analysis.get("translation"),
                "in_context": analysis.get("meaning_in_context"),
                "explanation": analysis.get("explanation"),
                "pitfall": analysis.get("pitfall"),
                "literal": analysis.get("literal"),
                "imagine": analysis.get("imagine"),
                "formality_note": analysis.get("formality_note"),
                "fits": fits(analysis.get("contexts", [])),
            },
            "mistake": mistake(analysis),
            "examples": [
                {"text": example["original"], "translation": example["translation"]}
                for example in analysis.get("examples", [])
            ],
            "collocations": analysis.get("collocations", []),
            "synonyms": analysis.get("synonyms", []),
            "antonyms": analysis.get("antonyms", []),
            "formality": analysis.get("formality"),
            "dialogue": [
                {
                    "speaker": line["speaker"],
                    "text": line["text"],
                    "translation": line["translation"],
                }
                for line in analysis.get("dialogue", [])
            ],
        }


class CardGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ("id", "name", "icon", "accent")


class CardSpanSerializer(serializers.ModelSerializer):
    term = serializers.UUIDField(source="term_id", allow_null=True, default=None)

    class Meta:
        model = CaptureTerm
        fields = ("text", "start", "end", "term")


class CardCaptureSerializer(serializers.ModelSerializer):
    terms = CardSpanSerializer(many=True, read_only=True)

    class Meta:
        model = Capture
        fields = ("id", "source", "text", "terms", "captured_at")


class TermDetailSerializer(serializers.BaseSerializer):
    def to_representation(self, detail):
        term = detail["term"]
        card = detail["card"]
        return {
            "id": str(term.id),
            "text": term.text,
            "translation": term.translation,
            "kind": term.kind,
            "level": term.level,
            "group": term.group and CardGroupSerializer(term.group).data,
            "revealed": card.revealed,
            "pitfall_revealed": card.pitfall_revealed,
            "formality_revealed": card.formality_revealed,
            "card": CardSerializer(card).data,
            "captures": CardCaptureSerializer(detail["captures"], many=True).data,
        }
