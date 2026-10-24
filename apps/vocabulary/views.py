from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response

from apps.vocabulary.serializers import (
    GroupCreateSerializer,
    GroupSerializer,
    MoveTermsSerializer,
    VocabularySerializer,
)
from apps.vocabulary.services import VocabularyService


@api_view(["GET"])
def vocabulary(request):
    return Response(VocabularySerializer(VocabularyService().vocabulary(request.user)).data)


@api_view(["POST"])
@parser_classes([JSONParser])
def create_group(request):
    serializer = GroupCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    group = VocabularyService().create_group(request.user, serializer.validated_data)

    return Response(GroupSerializer(group).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@parser_classes([JSONParser])
def move_terms(request):
    serializer = MoveTermsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = VocabularyService()
    service.move(
        request.user, serializer.validated_data["terms"], serializer.validated_data["group"]
    )

    return Response(VocabularySerializer(service.vocabulary(request.user)).data)
