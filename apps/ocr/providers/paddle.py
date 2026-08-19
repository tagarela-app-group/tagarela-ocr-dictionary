import tempfile
import threading
from pathlib import Path


class PaddleOCRProvider:
    _engine = None
    _lock = threading.Lock()

    def extract_text(self, image_file) -> str:
        image_path = self._write_temp_image(image_file)

        try:
            result = self._get_engine().predict(str(image_path))
            return self._join_texts(result)
        finally:
            image_path.unlink(missing_ok=True)
            image_file.seek(0)

    @classmethod
    def _get_engine(cls):
        if cls._engine is None:
            with cls._lock:
                if cls._engine is None:
                    from paddleocr import PaddleOCR

                    cls._engine = PaddleOCR(
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_textline_orientation=False,
                        engine="paddle",
                    )

        return cls._engine

    def _write_temp_image(self, image_file) -> Path:
        suffix = Path(image_file.name).suffix or ".img"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            for chunk in image_file.chunks():
                temp_file.write(chunk)

            return Path(temp_file.name)

    def _join_texts(self, result) -> str:
        texts = []

        for item in result:
            data = self._result_to_dict(item)
            texts.extend(data.get("rec_texts", []))

        return " ".join(text.strip() for text in texts if text and text.strip())

    def _result_to_dict(self, item) -> dict:
        if isinstance(item, dict):
            return item.get("res", item)

        if hasattr(item, "json"):
            data = item.json
            return data.get("res", data)

        if hasattr(item, "res"):
            return item.res

        return {}
