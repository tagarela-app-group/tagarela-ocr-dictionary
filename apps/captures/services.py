from django.db import IntegrityError, transaction
from django.http import Http404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import APIException

from apps.captures.models import Capture, CaptureTerm
from apps.captures.tasks import enqueue_processing
from apps.captures.uploads import delete_upload, save_upload

RECEIVES_FILE = {Capture.Status.WAITING_FILE, Capture.Status.PROCESSING, Capture.Status.FAILED}


class CaptureConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"


class CaptureService:
    def list(self, user, updated_since=None):
        captures = Capture.objects.filter(user=user).prefetch_related("terms")
        if updated_since is None:
            return captures.filter(discarded_at__isnull=True)

        return captures.filter(updated_at__gte=updated_since)

    def get(self, user, capture_id, include_discarded: bool = False) -> Capture:
        captures = Capture.objects.filter(user=user)
        if not include_discarded:
            captures = captures.filter(discarded_at__isnull=True)

        capture = captures.filter(pk=capture_id).first()
        if capture is None:
            raise Http404

        return capture

    def create(self, user, data: dict) -> tuple[Capture, bool]:
        existing = Capture.objects.filter(pk=data["id"]).first()
        if existing is not None:
            return self._same_owner(existing, user), False

        text = data.get("text", "")
        has_text = "text" in data
        try:
            with transaction.atomic():
                capture = Capture.objects.create(
                    id=data["id"],
                    user=user,
                    source=data["source"],
                    status=Capture.Status.READY if has_text else Capture.Status.WAITING_FILE,
                    original_text=text,
                    text=text,
                    captured_at=data["captured_at"],
                    processed_at=timezone.now() if has_text else None,
                )
        except IntegrityError:
            return self._same_owner(Capture.objects.get(pk=data["id"]), user), False

        return capture, True

    def receive_file(self, capture: Capture, file) -> Capture:
        if capture.status not in RECEIVES_FILE:
            raise CaptureConflict("Essa captura já foi processada.")

        save_upload(capture.id, file)
        capture.status = Capture.Status.PROCESSING
        capture.error = ""
        capture.save(update_fields=["status", "error", "updated_at"])
        transaction.on_commit(lambda: enqueue_processing(capture.id))

        return capture

    def update(self, capture: Capture, data: dict) -> Capture:
        if capture.status != Capture.Status.READY:
            raise CaptureConflict("Essa captura não pode ser editada agora.")

        with transaction.atomic():
            if "text" in data:
                capture.text = data["text"]
            capture.save(update_fields=["text", "updated_at"])

            if "terms" in data:
                capture.terms.all().delete()
                CaptureTerm.objects.bulk_create(
                    CaptureTerm(capture=capture, **term) for term in data["terms"]
                )
            elif "text" in data:
                stale = [
                    term.pk
                    for term in capture.terms.all()
                    if capture.text[term.start : term.end] != term.text
                ]
                capture.terms.filter(pk__in=stale).delete()

        return capture

    def confirm(self, capture: Capture) -> Capture:
        if capture.status == Capture.Status.ANALYZED:
            return capture
        if capture.status != Capture.Status.READY:
            raise CaptureConflict("Essa captura ainda não está pronta.")
        if not capture.terms.exists():
            raise serializers.ValidationError({"terms": ["Escolha pelo menos um termo."]})

        capture.status = Capture.Status.ANALYZED
        capture.analyzed_at = timezone.now()
        capture.save(update_fields=["status", "analyzed_at", "updated_at"])

        return capture

    def discard(self, capture: Capture) -> None:
        if capture.discarded_at is not None:
            return

        delete_upload(capture.id)
        capture.discarded_at = timezone.now()
        capture.save(update_fields=["discarded_at", "updated_at"])

    def _same_owner(self, capture: Capture, user) -> Capture:
        if capture.user_id != user.pk:
            raise CaptureConflict("Esse id já está em uso.")

        return capture
