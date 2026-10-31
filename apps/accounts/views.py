from allauth.headless.adapter import get_adapter
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.accounts.serializers import AccountInputSerializer
from apps.accounts.services import AccountService


@api_view(["PATCH"])
def account(request):
    serializer = AccountInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = AccountService().update(request.user, serializer.validated_data)

    return Response(get_adapter().serialize_user(user))
