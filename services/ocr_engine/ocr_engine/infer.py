"""Full-page OCR: segment a page into lines, recognise each, join top-to-bottom.

This is the inference entry point the API's ocr_client calls. It takes any Recognizer, so
the same assembly is exercised in tests (StubRecognizer) and in production (TrOCRRecognizer).
"""

from pathlib import Path

from PIL import Image

from ocr_engine.recognizer import Recognizer
from ocr_engine.segment import segment_lines


def extract_text_from_image(
    image_path: str | Path,
    recognizer: Recognizer,
    **segment_kwargs,
) -> str:
    """Return the recognised text of a report image, one line per detected text band."""
    image = Image.open(image_path)
    return extract_text_from_pil(image, recognizer, **segment_kwargs)


def extract_text_from_pil(image: Image.Image, recognizer: Recognizer, **segment_kwargs) -> str:
    lines = segment_lines(image, **segment_kwargs)
    if not lines:
        return ""
    texts = recognizer.recognize_batch([ln.image for ln in lines])
    return "\n".join(t for t in texts if t.strip())
