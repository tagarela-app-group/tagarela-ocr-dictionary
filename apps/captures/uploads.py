from pathlib import Path

from django.conf import settings


def save_upload(capture_id, file) -> Path:
    delete_upload(capture_id)
    settings.CAPTURE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = settings.CAPTURE_UPLOAD_DIR / f"{capture_id}{Path(file.name).suffix.lower()}"

    with path.open("wb") as target:
        for chunk in file.chunks():
            target.write(chunk)

    return path


def find_upload(capture_id) -> Path | None:
    return next(settings.CAPTURE_UPLOAD_DIR.glob(f"{capture_id}*"), None)


def delete_upload(capture_id) -> None:
    for path in settings.CAPTURE_UPLOAD_DIR.glob(f"{capture_id}*"):
        path.unlink(missing_ok=True)
