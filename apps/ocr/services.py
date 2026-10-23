from pathlib import Path

from apps.lexical.services import LexicalLookupService
from apps.ocr.providers.paddle import PaddleOCRProvider


class ImageAnalysisService:
    def __init__(
        self,
        ocr_provider: PaddleOCRProvider | None = None,
        lexical_service: LexicalLookupService | None = None,
    ) -> None:
        self.ocr_provider = ocr_provider or PaddleOCRProvider()
        self.lexical_service = lexical_service or LexicalLookupService()

    def analyze(self, image_file) -> dict:
        text = self.ocr_provider.extract_text(image_file)
        words = self.lexical_service.analyze_text(text)

        return {
            "ocr": {
                "text": text,
            },
            "words": words,
        }


class TextExtractionService:
    def __init__(self, ocr_provider: PaddleOCRProvider | None = None) -> None:
        self.ocr_provider = ocr_provider or PaddleOCRProvider()

    def extract(self, image_path: Path) -> str:
        return self.ocr_provider.extract_text_from_path(image_path)
