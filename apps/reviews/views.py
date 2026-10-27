from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response

from apps.courses.services import CourseService
from apps.exercises.kinds import KINDS
from apps.reviews.serializers import AttemptSerializer, SessionSerializer
from apps.reviews.services import ReviewService
from apps.vocabulary.serializers import TermSerializer


@api_view(["GET"])
def review_session(request):
    kinds = list(KINDS)
    if "kinds" in request.query_params:
        kinds = [kind for kind in request.query_params.getlist("kinds") if kind in KINDS]

    session = ReviewService().session(CourseService().active(request.user), kinds)

    return Response(SessionSerializer(session).data)


@api_view(["POST"])
@parser_classes([JSONParser])
def record_attempt(request):
    serializer = AttemptSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    term = ReviewService().record(request.user, serializer.validated_data)

    return Response({"term": TermSerializer(term).data}, status=status.HTTP_201_CREATED)
