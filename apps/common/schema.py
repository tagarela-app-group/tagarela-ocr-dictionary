from rest_framework import serializers


def json_schema(field: serializers.Field) -> dict[str, object]:
    match field:
        case serializers.ListSerializer() | serializers.ListField():
            return _array(field)
        case serializers.Serializer():
            return {
                "type": "object",
                "additionalProperties": False,
                "required": list(field.fields),
                "properties": {name: json_schema(child) for name, child in field.fields.items()},
            }
        case serializers.ChoiceField():
            return {"type": "string", "enum": list(field.choices)}
        case serializers.BooleanField():
            return _scalar("boolean", field)
        case serializers.CharField():
            return _scalar("string", field)
    raise TypeError(f"{type(field).__name__} has no JSON schema")


def _array(field: serializers.ListSerializer | serializers.ListField) -> dict[str, object]:
    schema: dict[str, object] = {"type": "array"}
    if field.min_length is not None:
        schema["minItems"] = field.min_length
    if field.max_length is not None:
        schema["maxItems"] = field.max_length
    schema["items"] = json_schema(field.child)

    return schema


def _scalar(kind: str, field: serializers.Field) -> dict[str, object]:
    return {"type": [kind, "null"] if field.allow_null else kind}
