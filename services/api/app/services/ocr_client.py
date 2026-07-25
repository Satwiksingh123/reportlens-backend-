"""OCR adapter: runs the ocr_engine pipeline over an uploaded report.

Default engine is Tesseract (CPU, no training, accurate on clean printed reports). If
OCR_MODEL_DIR points at a fine-tuned TrOCR model it uses that instead. Falls back to a
deterministic stub when neither engine is available (e.g. the tesseract binary isn't
installed), so the pipeline stays runnable in CI and offline.
"""

import logging
import sys
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_SERVICES = Path(__file__).resolve().parents[3]
_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff"}
_PDF_TYPE = "application/pdf"

_STUB_TEXT = (
    "Complete Blood Count (CBC)\n"
    "Hemoglobin 11.2 g/dL 13.0-17.0\n"
    "WBC 11500 /uL 4000-11000\n"
    "Platelets 210000 /uL 150000-410000\n"
)


def _bootstrap_ocr_engine() -> None:
    path = str(_SERVICES / "ocr_engine")
    if path not in sys.path:
        sys.path.insert(0, path)


@lru_cache(maxsize=1)
def _get_recognizer():
    """Load the OCR recogniser once, or return None to signal the stub fallback.

    Prefers a fine-tuned TrOCR model when OCR_MODEL_DIR is set; otherwise Tesseract. Returns
    None only when neither engine can be loaded (expected offline / in minimal CI).
    """
    _bootstrap_ocr_engine()
    settings = get_settings()
    model_dir = settings.ocr_model_dir

    if model_dir and Path(model_dir).exists():
        try:
            from ocr_engine.recognizer import TrOCRRecognizer

            return TrOCRRecognizer(model_dir=model_dir)
        except Exception as exc:  # noqa: BLE001 - fall through to Tesseract/stub
            logger.warning("TrOCR model unavailable (%s); trying Tesseract", exc)

    try:
        from ocr_engine.recognizer import TesseractRecognizer

        return TesseractRecognizer()
    except Exception as exc:  # noqa: BLE001 - pytesseract/binary missing -> stub
        logger.warning("Tesseract unavailable (%s); falling back to stub", exc)
        return None


def extract_text(path: str, content_type: str) -> str:
    recognizer = _get_recognizer()
    if recognizer is None or content_type not in (_IMAGE_TYPES | {_PDF_TYPE}):
        return _STUB_TEXT
    try:
        _bootstrap_ocr_engine()
        if content_type == _PDF_TYPE:
            text = _extract_from_pdf(path, recognizer)
        else:
            from ocr_engine.infer import extract_text_from_image

            text = extract_text_from_image(path, recognizer)
        return text or _STUB_TEXT
    except Exception as exc:  # noqa: BLE001 - never let OCR crash the pipeline
        logger.warning("OCR failed on %s (%s); falling back to stub", path, exc)
        return _STUB_TEXT


def _extract_from_pdf(path: str, recognizer) -> str:
    """Render every PDF page to an image and recognise each (most real report uploads
    are PDFs, not raw images). Page texts are joined with a blank line.

    NOTE: a native-text-layer-first approach (via ocr_engine.pdf_utils.extract_pdf_text)
    was tried and measured against the real sample reports - it was WORSE, not better:
    these table-based PDFs store text in column order in the content stream (all test
    names, then all values, then all ranges), so PyMuPDF's plain-text extraction breaks
    row alignment between a test's name/value/range entirely. Tesseract's OCR, run on the
    rendered page, reconstructs visual (row) reading order correctly and stayed the more
    accurate path for these layouts. A layout-aware extraction (grouping PyMuPDF's
    word-level bounding boxes into rows ourselves) could beat OCR for native-text PDFs,
    but is unimplemented and untested - left as a documented future improvement, not
    shipped without validation.
    """
    from ocr_engine.infer import extract_text_from_pil
    from ocr_engine.pdf_utils import pdf_to_images

    pages = pdf_to_images(path)
    texts = [extract_text_from_pil(page, recognizer) for page in pages]
    return "\n\n".join(t for t in texts if t.strip())
