from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from apps.ocr.providers.paddle import PaddleOCRProvider


class FakeEngine:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result or []
        self.error = error
        self.paths: list[Path] = []
        self.contents: list[bytes] = []

    def predict(self, path: str):
        self.paths.append(Path(path))
        self.contents.append(Path(path).read_bytes())

        if self.error:
            raise self.error

        return self.result


class PaddleOCRProviderTests(SimpleTestCase):
    def extract_text(self, engine: FakeEngine, image_file=None) -> str:
        image_file = image_file or SimpleUploadedFile("foto.png", b"image-bytes")

        with patch.object(PaddleOCRProvider, "_engine", engine):
            return PaddleOCRProvider().extract_text(image_file)

    def test_joins_rec_texts_ignoring_blank(self):
        engine = FakeEngine(
            [
                {"res": {"rec_texts": ["The", " quick ", ""]}},
                {"res": {"rec_texts": ["  ", "fox"]}},
            ]
        )

        self.assertEqual(self.extract_text(engine), "The quick fox")

    def test_reads_every_result_format(self):
        engine = FakeEngine(
            [
                {"rec_texts": ["a"]},
                SimpleNamespace(json={"res": {"rec_texts": ["b"]}}),
                SimpleNamespace(res={"rec_texts": ["c"]}),
                object(),
            ]
        )

        self.assertEqual(self.extract_text(engine), "a b c")

    def test_sends_upload_as_temp_file_removed_after(self):
        engine = FakeEngine()
        image_file = SimpleUploadedFile("foto.png", b"image-bytes")

        self.extract_text(engine, image_file)

        self.assertEqual(engine.contents, [b"image-bytes"])
        self.assertEqual(engine.paths[0].suffix, ".png")
        self.assertFalse(engine.paths[0].exists())
        self.assertEqual(image_file.tell(), 0)

    def test_removes_temp_file_when_engine_fails(self):
        engine = FakeEngine(error=RuntimeError("engine down"))

        with self.assertRaises(RuntimeError):
            self.extract_text(engine)

        self.assertFalse(engine.paths[0].exists())


class PaddleOCRProviderFromPathTests(SimpleTestCase):
    def test_reads_the_given_path_without_copying(self):
        engine = FakeEngine([{"res": {"rec_texts": ["MIND", "THE GAP"]}}])
        path = Path(__file__)

        with patch.object(PaddleOCRProvider, "_engine", engine):
            text = PaddleOCRProvider().extract_text_from_path(path)

        self.assertEqual(text, "MIND THE GAP")
        self.assertEqual(engine.paths, [path])
