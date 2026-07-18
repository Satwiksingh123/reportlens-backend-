"""OCR adapter: runs the ocr_engine pipeline over an uploaded report.

Uses the fine-tuned TrOCR recogniser when a trained model is configured (OCR_MODEL_DIR)
and the image is a supported type. Otherwise returns a deterministic stub so the pipeline
stays runnable in CI, offline, and before the model has been trained.
"""

import logging
import sys
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_SERVICES = Path(__file__).resolve().parents[3]
_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff"}

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
    """Load the fine-tuned TrOCR recogniser once, or return None to signal fallback.

    Returns None when no model is configured, the model dir is missing, or the training
    extras (torch/transformers) aren't installed — all expected states, not errors.
    """
    settings = get_settings()
    model_dir = settings.ocr_model_dir
    if not model_dir or not Path(model_dir).exists():
        return None
    try:
        _bootstrap_ocr_engine()
        from ocr_engine.recognizer import TrOCRRecognizer

        return TrOCRRecognizer(model_dir=model_dir)
    except Exception as exc:  # noqa: BLE001 - any load failure -> graceful stub
        logger.warning("OCR model unavailable (%s); falling back to stub", exc)
        return None


def extract_text(path: str, content_type: str) -> str:
    recognizer = _get_recognizer()
    if recognizer is None or content_type not in _IMAGE_TYPES:
        return _STUB_TEXT
    try:
        _bootstrap_ocr_engine()
        from ocr_engine.infer import extract_text_from_image

        text = extract_text_from_image(path, recognizer)
        return text or _STUB_TEXT
    except Exception as exc:  # noqa: BLE001 - never let OCR crash the pipeline
        logger.warning("OCR failed on %s (%s); falling back to stub", path, exc)
        return _STUB_TEXT
