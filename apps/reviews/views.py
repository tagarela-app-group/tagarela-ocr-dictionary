from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.courses.services import CourseService
from apps.exercises.kinds import KINDS
from apps.reviews.serializers import (
    AttemptSerializer,
    EffectSerializer,
    SessionQuerySerializer,
    SessionSerializer,
    StudySerializer,
)
from apps.reviews.services import ReviewService
from apps.vocabulary.serializers import TermSerializer


@api_view(["GET"])
def review_session(request):
    query = SessionQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)

    session = ReviewService().session(
        CourseService().active(request.user),
        [kind for kind in query.validated_data.get("kinds", KINDS) if kind in KINDS],
        query.validated_data.get("date"),
        query.validated_data["offset"],
    )

    return Response(SessionSerializer(session).data)


@api_view(["POST"])
def record_attempt(request):
    serializer = AttemptSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    attempt = ReviewService().record(request.user, serializer.validated_data)

    return Response(
        {"term": TermSerializer(attempt.term).data, "effect": EffectSerializer(attempt).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def ask_for_more(request):
    ReviewService().ask_for_more(CourseService().active(request.user))

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
def study_term(request, term_id):
    serializer = StudySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    term = ReviewService().study(request.user, term_id, serializer.validated_data["event"])

    return Response({"term": TermSerializer(term).data})
