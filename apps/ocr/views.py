from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.ocr.serializers import ImageAnalyzeSerializer
from apps.ocr.services import ImageAnalysisService


@api_view(["POST"])
@parser_classes([MultiPartParser])
def analyze_image(request):
    serializer = ImageAnalyzeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    result = ImageAnalysisService().analyze(serializer.validated_data["file"])

    return Response(result, status=status.HTTP_200_OK)
