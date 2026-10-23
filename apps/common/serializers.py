from collections.abc import Mapping

from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        unknown = {}
        if isinstance(data, Mapping):
            unknown = {
                field: ["Campo não permitido."] for field in sorted(set(data) - set(self.fields))
            }

        try:
            value = super().to_internal_value(data)
        except serializers.ValidationError as exc:
            if unknown and isinstance(exc.detail, dict):
                raise serializers.ValidationError({**exc.detail, **unknown}) from exc
            raise

        if unknown:
            raise serializers.ValidationError(unknown)

        return value
