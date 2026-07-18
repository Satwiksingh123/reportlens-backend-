from app.services.llm_client import explain
from app.services.ocr_client import extract_text
from app.services.parser_client import parse


def test_parser_on_ocr_stub_extracts_cbc():
    text = extract_text("dummy.pdf", "application/pdf")
    rows = parse(text)
    names = {r["test_name"] for r in rows}
    assert "Hemoglobin" in names
    assert all("status" in r for r in rows)


def test_hemoglobin_flagged_low_from_stub():
    text = extract_text("dummy.pdf", "application/pdf")
    rows = parse(text)
    hb = next(r for r in rows if r["test_name"] == "Hemoglobin")
    assert hb["status"] == "Low"  # stub value 11.2 vs 13.0-17.0


def test_explainer_flags_abnormal_and_disclaims():
    rows = parse(extract_text("dummy.pdf", "application/pdf"))
    enriched, summary = explain(rows)
    assert all("explanation" in r for r in enriched)
    assert "consult a qualified doctor" in summary.lower()
