from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.courses.services import CourseService
from apps.daily_words.serializers import DailyWordSerializer
from apps.daily_words.services import DailyWordService


@api_view(["GET"])
def daily_word(request):
    word = DailyWordService().today(CourseService().active(request.user))

    return Response(DailyWordSerializer(word).data)


@api_view(["POST"])
def save_daily_word(request):
    word = DailyWordService().save(CourseService().active(request.user))

    return Response(DailyWordSerializer(word).data, status=status.HTTP_201_CREATED)
