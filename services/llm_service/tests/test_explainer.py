from llm_service.explainer import explain_biomarkers

ROWS = [
    {"test_name": "Hemoglobin", "value": "11.2", "unit": "g/dL",
     "reference_range": "13.0-17.0", "status": "Low"},
    {"test_name": "Platelet Count", "value": "210000", "unit": "/uL",
     "reference_range": "150000-410000", "status": "Normal"},
]


def test_fallback_explanations_present_without_model():
    enriched, summary = explain_biomarkers(ROWS, client=None)
    assert len(enriched) == 2
    for row in enriched:
        assert row["explanation"]
        assert "consult a qualified doctor" in row["explanation"].lower()


def test_summary_lists_abnormal():
    _, summary = explain_biomarkers(ROWS, client=None)
    assert "Hemoglobin" in summary
    assert "educational explanation" in summary.lower()


def test_all_normal_summary():
    rows = [{"test_name": "TSH", "value": "2.0", "unit": "uIU/mL",
             "reference_range": "0.4-4.0", "status": "Normal"}]
    _, summary = explain_biomarkers(rows, client=None)
    assert "within their reference ranges" in summary


def test_retriever_notes_attached_as_evidence():
    def retriever(name: str) -> str:
        return f"Notes about {name}."

    enriched, _ = explain_biomarkers(ROWS, retriever=retriever, client=None)
    assert enriched[0]["evidence"]["reference_notes"] == "Notes about Hemoglobin."
