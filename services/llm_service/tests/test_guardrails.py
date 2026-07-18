from llm_service.guardrails import DISCLAIMER, apply_guardrails


def test_disclaimer_appended_when_missing():
    r = apply_guardrails("Your hemoglobin is a bit low.")
    assert DISCLAIMER in r.text


def test_disclaimer_not_duplicated():
    text = f"Your hemoglobin is a bit low. {DISCLAIMER}"
    r = apply_guardrails(text)
    assert r.text.count("educational explanation") == 1


def test_removes_medication_dosage():
    text = "Your iron is low. Take 65 mg of ferrous sulphate twice daily."
    r = apply_guardrails(text)
    assert "65 mg" not in r.text
    assert any("prescriptive" in f for f in r.flagged)


def test_removes_prescribe_language():
    text = "This is high. I prescribe atorvastatin for you."
    r = apply_guardrails(text)
    assert "prescribe" not in r.text.lower()
    assert r.flagged


def test_softens_diagnostic_claim():
    text = "This means you have diabetes."
    r = apply_guardrails(text)
    assert "you have diabetes" not in r.text.lower()
    assert any("diagnostic" in f for f in r.flagged)


def test_safe_text_passes_through():
    text = (
        "Hemoglobin carries oxygen in your blood. A slightly low value can relate to "
        "reduced iron; eating iron-rich foods may help."
    )
    r = apply_guardrails(text)
    assert not r.flagged
    assert text.split(".")[0] in r.text
