from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cards.serializers import RevealSerializer, TermDetailSerializer
from apps.cards.services import TermCardService


class TermDetailView(APIView):
    parser_classes = [JSONParser]

    def get(self, request, term_id):
        detail = TermCardService().detail(request.user, term_id)

        return Response(TermDetailSerializer(detail).data)

    def patch(self, request, term_id):
        serializer = RevealSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        detail = TermCardService().reveal(request.user, term_id, serializer.validated_data)

        return Response(TermDetailSerializer(detail).data)
