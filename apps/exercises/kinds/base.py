import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum

from rest_framework import serializers

from apps.common.schema import json_schema

type Payload = Mapping[str, object]


class Effort(StrEnum):
    READ = "read"
    LISTEN = "listen"
    PRODUCE = "produce"


@dataclass(frozen=True)
class Brief:
    focus: str
    focus_kind: str
    source_language: str
    target_language: str
    meaning: str | None
    count: int


class ExerciseKind:
    name: str
    effort: Effort
    prompt_version: str
    system_prompt: str
    item_serializer: type[serializers.Serializer]

    def build_input(self, brief: Brief) -> str:
        return "Write exercises for this untrusted language-learning input:\n" + json.dumps(
            asdict(brief), ensure_ascii=False, separators=(",", ":")
        )

    def response_schema(self, count: int) -> Mapping[str, object]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["items"],
            "properties": {
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": count,
                    "items": json_schema(self.item_serializer()),
                }
            },
        }

    def payloads(self, response: Mapping[str, object]) -> list[Payload]:
        items = response.get("items")
        if not isinstance(items, list):
            return []

        payloads: list[Payload] = []
        for item in items:
            serializer = self.item_serializer(data=item)
            if not serializer.is_valid():
                continue
            payload = self.to_payload(serializer.validated_data)
            if payload is not None and payload not in payloads:
                payloads.append(payload)

        return payloads

    def to_payload(self, item: Mapping[str, str]) -> Payload | None:
        raise NotImplementedError
