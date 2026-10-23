from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from apps.ocr.services import ImageAnalysisService, TextExtractionService


class FakeOCRProvider:
    def __init__(self, text: str) -> None:
        self.text = text
        self.files = []

    def extract_text(self, image_file) -> str:
        self.files.append(image_file)
        return self.text


class FakeLexicalService:
    def __init__(self, words: list[dict]) -> None:
        self.words = words
        self.texts = []

    def analyze_text(self, text: str) -> list[dict]:
        self.texts.append(text)
        return self.words


class ImageAnalysisServiceTests(SimpleTestCase):
    def test_sends_ocr_text_to_lexical_and_returns_both(self):
        words = [{"word": "fox", "definitions": ["A canine."], "source": "dictionary"}]
        ocr_provider = FakeOCRProvider("The fox")
        lexical_service = FakeLexicalService(words)
        image_file = SimpleUploadedFile("foto.png", b"image-bytes")

        result = ImageAnalysisService(ocr_provider, lexical_service).analyze(image_file)

        self.assertEqual(result, {"ocr": {"text": "The fox"}, "words": words})
        self.assertEqual(ocr_provider.files, [image_file])
        self.assertEqual(lexical_service.texts, ["The fox"])


class FakePathProvider:
    def __init__(self, text: str) -> None:
        self.text = text
        self.paths = []

    def extract_text_from_path(self, image_path: Path) -> str:
        self.paths.append(image_path)
        return self.text


class TextExtractionServiceTests(SimpleTestCase):
    def test_returns_only_the_text_of_the_image(self):
        provider = FakePathProvider("MIND THE GAP")
        path = Path("/tmp/foto.png")

        text = TextExtractionService(provider).extract(path)

        self.assertEqual(text, "MIND THE GAP")
        self.assertEqual(provider.paths, [path])
