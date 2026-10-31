from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.services import CourseService
from apps.vocabulary.serializers import (
    GroupInputSerializer,
    GroupSerializer,
    MoveTermsSerializer,
    TermsSerializer,
    VocabularySerializer,
)
from apps.vocabulary.services import VocabularyService


def vocabulary_response(service: VocabularyService, course) -> Response:
    return Response(VocabularySerializer(service.vocabulary(course)).data)


@api_view(["GET"])
def vocabulary(request):
    return vocabulary_response(VocabularyService(), CourseService().active(request.user))


@api_view(["POST"])
def create_group(request):
    serializer = GroupInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    group = VocabularyService().create_group(
        CourseService().ensure_active(request.user), serializer.validated_data
    )

    return Response(GroupSerializer(group).data, status=status.HTTP_201_CREATED)


class GroupDetailView(APIView):
    def patch(self, request, group_id):
        serializer = GroupInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        service = VocabularyService()
        group = service.update_group(
            service.group(CourseService().active(request.user), group_id),
            serializer.validated_data,
        )

        return Response(GroupSerializer(group).data)

    def delete(self, request, group_id):
        service = VocabularyService()
        course = CourseService().active(request.user)
        service.delete_group(service.group(course, group_id))

        return vocabulary_response(service, course)


@api_view(["POST"])
def move_terms(request):
    serializer = MoveTermsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = VocabularyService()
    course = CourseService().active(request.user)
    service.move(course, serializer.validated_data["terms"], serializer.validated_data["group"])

    return vocabulary_response(service, course)


@api_view(["POST"])
def delete_terms(request):
    serializer = TermsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = VocabularyService()
    course = CourseService().active(request.user)
    service.delete_terms(course, serializer.validated_data["terms"])

    return vocabulary_response(service, course)


@api_view(["POST"])
def restore_terms(request):
    serializer = TermsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = VocabularyService()
    course = CourseService().active(request.user)
    service.restore_terms(course, serializer.validated_data["terms"])

    return vocabulary_response(service, course)
