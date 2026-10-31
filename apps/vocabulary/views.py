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


def active_course(request):
    return CourseService().active(request.user)


@api_view(["GET"])
def vocabulary(request):
    return vocabulary_response(VocabularyService(), active_course(request))


@api_view(["POST"])
def create_group(request):
    serializer = GroupInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    group = VocabularyService().create_group(active_course(request), serializer.validated_data)

    return Response(GroupSerializer(group).data, status=status.HTTP_201_CREATED)


class GroupDetailView(APIView):
    def patch(self, request, group_id):
        serializer = GroupInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        service = VocabularyService()
        group = service.update_group(
            service.group(active_course(request), group_id), serializer.validated_data
        )

        return Response(GroupSerializer(group).data)

    def delete(self, request, group_id):
        service = VocabularyService()
        course = active_course(request)
        service.delete_group(service.group(course, group_id))

        return vocabulary_response(service, course)


@api_view(["POST"])
def move_terms(request):
    serializer = MoveTermsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = VocabularyService()
    course = active_course(request)
    service.move(course, serializer.validated_data["terms"], serializer.validated_data["group"])

    return vocabulary_response(service, course)


@api_view(["POST"])
def delete_terms(request):
    serializer = TermsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = VocabularyService()
    course = active_course(request)
    service.delete_terms(course, serializer.validated_data["terms"])

    return vocabulary_response(service, course)


@api_view(["POST"])
def restore_terms(request):
    serializer = TermsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = VocabularyService()
    course = active_course(request)
    service.restore_terms(course, serializer.validated_data["terms"])

    return vocabulary_response(service, course)
