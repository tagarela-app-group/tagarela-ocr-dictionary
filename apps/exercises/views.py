from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.exercises.serializers import ExerciseSerializer
from apps.exercises.services import ExerciseService


@api_view(["GET"])
def term_exercises(request, term_id, kind):
    exercises = ExerciseService().exercises(request.user, term_id, kind)

    return Response({"exercises": ExerciseSerializer(exercises, many=True).data})
