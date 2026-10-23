from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def uploaded_image(
    image_format: str = "PNG",
    content_type: str = "image/png",
    name: str = "foto.png",
) -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (10, 10), "white").save(buffer, format=image_format)

    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)
