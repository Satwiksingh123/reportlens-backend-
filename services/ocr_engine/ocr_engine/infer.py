"""Full-page OCR entry point the API's ocr_client calls.

Two paths, chosen by the recogniser:
  - Whole-page recognisers (Tesseract, via a `read_page` method) get the full image and use
    their own layout analysis - most accurate (~99% on clean reports).
  - Line-crop recognisers (TrOCR, Stub) go through classical line segmentation, and each
    line crop is recognised then joined top-to-bottom.
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
    """Return the recognised text of a report image."""
    image = Image.open(image_path)
    return extract_text_from_pil(image, recognizer, **segment_kwargs)


def extract_text_from_pil(image: Image.Image, recognizer: Recognizer, **segment_kwargs) -> str:
    # Prefer whole-page recognition when the engine supports it (Tesseract's own layout
    # analysis beats feeding it pre-cut line crops).
    read_page = getattr(recognizer, "read_page", None)
    if callable(read_page):
        return read_page(image).strip()

    lines = segment_lines(image, **segment_kwargs)
    if not lines:
        return ""
    texts = recognizer.recognize_batch([ln.image for ln in lines])
    return "\n".join(t.strip() for t in texts if t.strip())
