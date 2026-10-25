from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.serializers import CourseInputSerializer, CourseSerializer
from apps.courses.services import CourseService


class CourseListView(APIView):
    parser_classes = [JSONParser]

    def get(self, request):
        courses = CourseService().courses(request.user)

        return Response(CourseSerializer(courses, many=True).data)

    def post(self, request):
        serializer = CourseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = CourseService()
        course, created = service.start(request.user, **serializer.validated_data)

        return Response(
            CourseSerializer(service.course(request.user, course.pk)).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CourseActivateView(APIView):
    def post(self, request, course_id):
        service = CourseService()
        course = service.activate(service.course(request.user, course_id))

        return Response(CourseSerializer(service.course(request.user, course.pk)).data)
