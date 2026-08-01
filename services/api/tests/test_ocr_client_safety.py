"""The OCR adapter must never invent text.

Found by uploading a blank 1x1 PNG through the real UI: the app returned a complete,
confident blood report - Hemoglobin 11.2 "Low", WBC 11500 "High", Platelets 210000
"Normal" - with full LLM explanations telling the user they might have an infection. None
of it came from the uploaded file. `extract_text` substituted a canned CBC fixture whenever
OCR returned nothing or raised, and that fabrication flowed downstream as if it were the
patient's own results.

These tests pin the corrected contract:
  - nothing readable  -> "" (honest; becomes zero biomarkers, which the UI explains)
  - no OCR engine     -> raise (report fails) unless the stub is explicitly enabled
  - OCR raises        -> propagate (report fails), never a canned result
"""

import sys
from pathlib import Path

import pytest

_API_ROOT = Path(__file__).resolve().parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from app.services import ocr_client  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_caches():
    # ocr_engine lives in a sibling package that isn't pip-installed; the adapter puts it on
    # sys.path lazily. Do the same here so monkeypatching "ocr_engine.infer..." can resolve
    # the module (otherwise these tests fail with ModuleNotFoundError wherever the sibling
    # packages aren't already imported - e.g. a bare CI run of just this file).
    ocr_client._bootstrap_ocr_engine()

    ocr_client._get_recognizer.cache_clear()
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    ocr_client._get_recognizer.cache_clear()
    get_settings.cache_clear()


class _Recognizer:
    """Stands in for a working OCR engine returning a fixed string."""

    def __init__(self, text: str):
        self._text = text

    def read_page(self, _image):
        return self._text


def test_unreadable_image_returns_empty_not_canned_results(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr_client, "_get_recognizer", lambda: _Recognizer(""))
    monkeypatch.setattr(
        ocr_client, "_extract_from_pdf", lambda *a, **k: pytest.fail("PDF path not expected")
    )
    monkeypatch.setattr(
        "ocr_engine.infer.extract_text_from_image", lambda *a, **k: "", raising=False
    )

    img = tmp_path / "blank.png"
    img.write_bytes(b"")

    text = ocr_client.extract_text(str(img), "image/png")
    assert text == ""
    assert "Hemoglobin" not in text, "canned CBC text must never be returned"


def test_whitespace_only_ocr_is_also_treated_as_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr_client, "_get_recognizer", lambda: _Recognizer("   \n\n  "))
    monkeypatch.setattr(
        "ocr_engine.infer.extract_text_from_image", lambda *a, **k: "   \n\n  ", raising=False
    )
    img = tmp_path / "blank.png"
    img.write_bytes(b"")
    assert ocr_client.extract_text(str(img), "image/png") == ""


def test_missing_ocr_engine_raises_instead_of_faking(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr_client, "_get_recognizer", lambda: None)
    monkeypatch.setenv("OCR_STUB_ENABLED", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()

    img = tmp_path / "x.png"
    img.write_bytes(b"")
    with pytest.raises(ocr_client.OcrUnavailableError):
        ocr_client.extract_text(str(img), "image/png")


def test_stub_only_when_explicitly_enabled(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr_client, "_get_recognizer", lambda: None)
    monkeypatch.setenv("OCR_STUB_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    img = tmp_path / "x.png"
    img.write_bytes(b"")
    assert "Hemoglobin" in ocr_client.extract_text(str(img), "image/png")


def test_ocr_errors_propagate_so_the_report_fails(monkeypatch, tmp_path):
    def boom(*_a, **_k):
        raise RuntimeError("tesseract exploded")

    monkeypatch.setattr(ocr_client, "_get_recognizer", lambda: _Recognizer("ignored"))
    monkeypatch.setattr("ocr_engine.infer.extract_text_from_image", boom, raising=False)

    img = tmp_path / "x.png"
    img.write_bytes(b"")
    with pytest.raises(RuntimeError, match="tesseract exploded"):
        ocr_client.extract_text(str(img), "image/png")


def test_unknown_content_type_raises_rather_than_returning_a_result(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr_client, "_get_recognizer", lambda: _Recognizer("whatever"))
    f = tmp_path / "x.bin"
    f.write_bytes(b"")
    with pytest.raises(ocr_client.OcrUnavailableError):
        ocr_client.extract_text(str(f), "application/octet-stream")
