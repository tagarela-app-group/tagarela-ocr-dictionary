from rest_framework import serializers

from apps.accounts.countries import COUNTRY_CODES
from apps.common.serializers import StrictSerializer


class AccountInputSerializer(StrictSerializer):
    country = serializers.ChoiceField(
        choices=sorted(COUNTRY_CODES),
        allow_blank=True,
        error_messages={
            "required": "Escolha um país.",
            "invalid_choice": "Escolha um país da lista.",
        },
    )
