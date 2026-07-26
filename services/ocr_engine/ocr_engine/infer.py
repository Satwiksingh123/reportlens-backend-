"""Full-page OCR entry point the API's ocr_client calls.

Every page is preprocessed first (deskew + lighting flattening), then recognised by one of
two paths depending on the recogniser:
  - Whole-page recognisers (Tesseract, via a `read_page` method) get the full image and use
    their own layout analysis - most accurate.
  - Line-crop recognisers (TrOCR, Stub) go through classical line segmentation, and each
    line crop is recognised then joined top-to-bottom.

Preprocessing runs unconditionally rather than only for "photos", because it was measured
to help photographed pages substantially while leaving clean PDF renders untouched:

    level      no preprocessing      with preprocessing
    clean      100.0%  (0 wrong)     100.0%  (0 wrong)   <- no regression
    light       87.9%  (2 wrong)      99.0%  (1 wrong)
    moderate    91.9%  (3 wrong)     100.0%  (0 wrong)

(value-level accuracy over 4 real reports x 3 simulated captures; see
`ocr_engine.photo_sim` and sample_reports/README.md). Detecting "is this a photo?" would be
an extra guess that buys nothing, since deskew self-skips a straight page.
"""

from pathlib import Path

from PIL import Image

from ocr_engine.preprocess import prepare_photo
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


def extract_text_from_pil(
    image: Image.Image,
    recognizer: Recognizer,
    preprocess: bool = True,
    **segment_kwargs,
) -> str:
    """Recognise a page. `preprocess=False` skips deskew/lighting correction (useful for
    measuring the preprocessing's own contribution)."""
    if preprocess:
        image = prepare_photo(image)

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
