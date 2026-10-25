from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.language_analysis.serializers import LanguageAnalysisRequestSerializer
from apps.language_analysis.services import LinguisticAnalysisService


class LanguageAnalysisView(APIView):
    parser_classes = [JSONParser]

    def post(self, request: Request) -> Response:
        serializer = LanguageAnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(LinguisticAnalysisService().analyze(serializer.validated_data))
