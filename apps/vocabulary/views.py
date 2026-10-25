from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.vocabulary.serializers import (
    GroupInputSerializer,
    GroupSerializer,
    MoveTermsSerializer,
    TermsSerializer,
    VocabularySerializer,
)
from apps.vocabulary.services import VocabularyService


def vocabulary_response(service: VocabularyService, user) -> Response:
    return Response(VocabularySerializer(service.vocabulary(user)).data)


@api_view(["GET"])
def vocabulary(request):
    return vocabulary_response(VocabularyService(), request.user)


@api_view(["POST"])
@parser_classes([JSONParser])
def create_group(request):
    serializer = GroupInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    group = VocabularyService().create_group(request.user, serializer.validated_data)

    return Response(GroupSerializer(group).data, status=status.HTTP_201_CREATED)


class GroupDetailView(APIView):
    parser_classes = [JSONParser]

    def patch(self, request, group_id):
        serializer = GroupInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        service = VocabularyService()
        group = service.update_group(
            service.group(request.user, group_id), serializer.validated_data
        )

        return Response(GroupSerializer(group).data)

    def delete(self, request, group_id):
        service = VocabularyService()
        service.delete_group(service.group(request.user, group_id))

        return vocabulary_response(service, request.user)


@api_view(["POST"])
@parser_classes([JSONParser])
def move_terms(request):
    serializer = MoveTermsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = VocabularyService()
    service.move(
        request.user, serializer.validated_data["terms"], serializer.validated_data["group"]
    )

    return vocabulary_response(service, request.user)


@api_view(["POST"])
@parser_classes([JSONParser])
def delete_terms(request):
    serializer = TermsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = VocabularyService()
    service.delete_terms(request.user, serializer.validated_data["terms"])

    return vocabulary_response(service, request.user)


@api_view(["POST"])
@parser_classes([JSONParser])
def restore_terms(request):
    serializer = TermsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = VocabularyService()
    service.restore_terms(request.user, serializer.validated_data["terms"])

    return vocabulary_response(service, request.user)
