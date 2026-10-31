from django.conf import settings
from rest_framework import status
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.captures.serializers import (
    CaptureCreateSerializer,
    CaptureListParamsSerializer,
    CaptureSerializer,
    CaptureUpdateSerializer,
)
from apps.captures.services import CaptureService


class CapturePagination(CursorPagination):
    page_size = settings.CAPTURE_PAGE_SIZE
    ordering = "-updated_at"


class CaptureListView(APIView):
    def get(self, request):
        params = CaptureListParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        captures = CaptureService().list(request.user, params.validated_data.get("updated_since"))
        paginator = CapturePagination()
        page = paginator.paginate_queryset(captures, request, view=self)

        return paginator.get_paginated_response(CaptureSerializer(page, many=True).data)

    def post(self, request):
        serializer = CaptureCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        capture, created = CaptureService().create(request.user, serializer.validated_data)

        return Response(
            CaptureSerializer(capture).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CaptureDetailView(APIView):
    def get(self, request, capture_id):
        capture = CaptureService().get(request.user, capture_id)

        return Response(CaptureSerializer(capture).data)

    def patch(self, request, capture_id):
        service = CaptureService()
        capture = service.get(request.user, capture_id)
        serializer = CaptureUpdateSerializer(capture, data=request.data)
        serializer.is_valid(raise_exception=True)

        capture = service.update(capture, serializer.validated_data)

        return Response(CaptureSerializer(capture).data)

    def delete(self, request, capture_id):
        service = CaptureService()
        service.discard(service.get(request.user, capture_id, include_discarded=True))

        return Response(status=status.HTTP_204_NO_CONTENT)


class CaptureConfirmView(APIView):
    def post(self, request, capture_id):
        service = CaptureService()
        capture = service.confirm(service.get(request.user, capture_id))

        return Response(CaptureSerializer(capture).data)
