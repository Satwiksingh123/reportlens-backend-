"""Full-page OCR: segment into lines, recognise each line, join top-to-bottom.

This is the inference entry point the API's ocr_client calls. Each segmented line crop is
recognised as a whole (Tesseract, the default engine, reads a full text line natively and
preserves the spacing between columns), then lines are joined with newlines. Takes any
Recognizer, so the same assembly is exercised in tests (StubRecognizer) and in production.
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
    return "\n".join(t.strip() for t in texts if t.strip())
