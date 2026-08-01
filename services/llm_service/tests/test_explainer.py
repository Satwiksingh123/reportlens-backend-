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


# --- regression: a report with nothing readable must not be summarised as "all normal" ---


def test_no_biomarkers_does_not_claim_everything_is_normal():
    """Found by uploading a blank image through the real UI: the pipeline produced zero
    biomarkers and the summary still read "All measured values are within their reference
    ranges" - telling a user whose report was never read that their results are fine."""
    _, summary = explain_biomarkers([], client=None)
    assert "within their reference ranges" not in summary.lower()
    assert "no lab values could be read" in summary.lower()
    assert "consult a qualified doctor" in summary.lower()


def test_no_biomarkers_never_calls_the_model():
    """With nothing to ground on, a model asked to summarise an empty list can only invent."""

    class ExplodingClient:
        def is_available(self):
            return True

        def generate(self, *a, **k):
            raise AssertionError("the model must not be consulted when there are no results")

    enriched, summary = explain_biomarkers([], client=ExplodingClient())
    assert enriched == []
    assert "no lab values could be read" in summary.lower()
