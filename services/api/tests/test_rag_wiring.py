"""RAG wiring: the API explainer grounds rows in curated notes, and the persist step
projects enriched rows safely onto StructuredResult columns."""

from app.services.llm_client import _get_retriever, explain
from app.services.ocr_client import extract_text
from app.services.parser_client import parse
from app.tasks.pipeline import _result_kwargs


def test_retriever_available_and_grounds_known_biomarker():
    retriever = _get_retriever()
    assert retriever is not None, "rag package should be importable"
    notes = retriever("Hemoglobin")
    assert "oxygen" in notes.lower()


def test_explain_attaches_evidence_from_rag():
    rows = parse(extract_text("dummy.pdf", "application/pdf"))
    enriched, _ = explain(rows)
    hb = next(r for r in enriched if r["test_name"] == "Hemoglobin")
    assert hb["evidence"] and "reference_notes" in hb["evidence"]
    assert hb["evidence"]["reference_notes"]


def test_result_kwargs_drops_unknown_keys_and_folds_flags():
    row = {
        "panel": "CBC",
        "test_name": "Hemoglobin",
        "value": "11.2",
        "unit": "g/dL",
        "reference_range": "13.0-17.0",
        "status": "Low",
        "explanation": "…",
        "evidence": {"reference_notes": "n"},
        "guardrail_flags": ["added_disclaimer"],
        "some_future_key": "ignored",
    }
    kwargs = _result_kwargs(row)
    assert "some_future_key" not in kwargs
    assert "guardrail_flags" not in kwargs  # folded, not a column
    assert kwargs["evidence"]["guardrail_flags"] == ["added_disclaimer"]
    assert kwargs["evidence"]["reference_notes"] == "n"


def test_result_kwargs_without_flags_or_evidence_is_safe():
    row = {"test_name": "TSH", "value": "3.0", "guardrail_flags": None}
    kwargs = _result_kwargs(row)
    assert kwargs == {"test_name": "TSH", "value": "3.0"}
