"""Parser + explainer wiring, exercised on a fixed sample of OCR-shaped text.

Uses the canned text directly instead of calling extract_text(): these tests are about what
happens to text once it exists, not about OCR. Routing them through extract_text() was also
how that canned CBC came to be treated as a legitimate production result - the fabrication
bug documented in test_ocr_client_safety.py.
"""

from app.services.llm_client import explain
from app.services.ocr_client import _STUB_TEXT
from app.services.parser_client import parse


def test_parser_extracts_cbc_from_ocr_text():
    rows = parse(_STUB_TEXT)
    names = {r["test_name"] for r in rows}
    assert "Hemoglobin" in names
    assert all("status" in r for r in rows)


def test_hemoglobin_flagged_low():
    rows = parse(_STUB_TEXT)
    hb = next(r for r in rows if r["test_name"] == "Hemoglobin")
    assert hb["status"] == "Low"  # 11.2 against a 13.0-17.0 reference range


def test_explainer_flags_abnormal_and_disclaims():
    enriched, summary = explain(parse(_STUB_TEXT))
    assert all("explanation" in r for r in enriched)
    assert "consult a qualified doctor" in summary.lower()
