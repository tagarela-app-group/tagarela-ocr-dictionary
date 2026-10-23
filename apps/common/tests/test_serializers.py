from django.http import QueryDict
from django.test import SimpleTestCase
from rest_framework import serializers

from apps.common.serializers import StrictSerializer


class Child(StrictSerializer):
    word = serializers.CharField()


class Parent(StrictSerializer):
    name = serializers.CharField()
    children = Child(many=True, required=False)


class StrictSerializerTests(SimpleTestCase):
    def test_known_fields_pass(self):
        serializer = Parent(data={"name": "Ana", "children": [{"word": "fox"}]})

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_unknown_field_is_rejected(self):
        serializer = Parent(data={"name": "Ana", "admin": True, "age": 3})

        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors,
            {"admin": ["Campo não permitido."], "age": ["Campo não permitido."]},
        )

    def test_unknown_field_in_nested_item_is_rejected(self):
        serializer = Parent(data={"name": "Ana", "children": [{"word": "fox", "extra": 1}]})

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["children"][0], {"extra": ["Campo não permitido."]})

    def test_unknown_and_invalid_fields_are_reported_together(self):
        serializer = Parent(data={"name": "", "admin": True})

        self.assertFalse(serializer.is_valid())
        self.assertEqual(set(serializer.errors), {"name", "admin"})

    def test_query_dict_is_checked(self):
        serializer = Parent(data=QueryDict("name=Ana&debug=1"))

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {"debug": ["Campo não permitido."]})
