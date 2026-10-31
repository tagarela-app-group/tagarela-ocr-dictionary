from django.test import SimpleTestCase
from rest_framework import serializers

from apps.common.schema import json_schema


class Line(serializers.Serializer):
    speaker = serializers.ChoiceField(choices=("A", "B"))
    done = serializers.BooleanField()
    note = serializers.CharField(allow_null=True)


class Card(serializers.Serializer):
    lines = Line(many=True, min_length=2, max_length=4)
    words = serializers.ListField(child=serializers.CharField(), max_length=5)


class JsonSchemaTests(SimpleTestCase):
    def test_every_field_is_required_and_nothing_else_is_allowed(self) -> None:
        schema = json_schema(Line())

        self.assertEqual(schema["required"], ["speaker", "done", "note"])
        self.assertIs(schema["additionalProperties"], False)

    def test_null_is_only_allowed_where_the_serializer_allows_it(self) -> None:
        properties = json_schema(Line())["properties"]

        self.assertEqual(properties["note"], {"type": ["string", "null"]})
        self.assertEqual(properties["done"], {"type": "boolean"})
        self.assertEqual(properties["speaker"], {"type": "string", "enum": ["A", "B"]})

    def test_lists_carry_their_limits_and_item_shape(self) -> None:
        properties = json_schema(Card())["properties"]

        self.assertEqual(properties["lines"]["minItems"], 2)
        self.assertEqual(properties["lines"]["maxItems"], 4)
        self.assertEqual(properties["lines"]["items"], json_schema(Line()))
        self.assertEqual(
            properties["words"], {"type": "array", "maxItems": 5, "items": {"type": "string"}}
        )
        self.assertNotIn("minItems", properties["words"])

    def test_unknown_field_type_fails_instead_of_asking_for_anything(self) -> None:
        with self.assertRaises(TypeError):
            json_schema(serializers.IntegerField())
