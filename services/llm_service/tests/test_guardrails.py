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


# --- regressions found by running a REAL model (qwen2.5:3b via Ollama) end-to-end ---


def test_lab_value_in_mg_units_is_not_treated_as_a_dosage():
    # The real model's most useful sentence states the patient's own measured value in
    # mg-based units. An earlier bare "<number> mg" rule deleted exactly that sentence,
    # so the user never saw their own result.
    text = (
        "Your calcium was measured at 9.00 mg/dL, which falls within the normal range "
        "of 8.60 to 10.20 mg/dL."
    )
    r = apply_guardrails(text)
    assert "9.00 mg/dL" in r.text
    assert not r.flagged


def test_real_dosage_phrasing_still_removed():
    for text in [
        "Take 500 mg of calcium daily.",
        "You should take 2 tablets after meals.",
        "The usual dose of 5 mg is enough.",
        "Consider taking 1000 IU of vitamin D.",
    ]:
        r = apply_guardrails(text)
        assert r.flagged, f"should have been flagged: {text!r}"


def test_innocent_you_have_is_not_mangled():
    # Real model output: "...so if you have any concerns, it's best to discuss them with
    # your provider." The old broad rule rewrote this into "so if may be associated with
    # any concerns", producing broken English in a medical explanation.
    text = "If you have any concerns, it is best to discuss them with your doctor."
    r = apply_guardrails(text)
    assert "if you have any concerns" in r.text.lower()
    assert not r.flagged


def test_diagnostic_softening_still_applies_to_conditions():
    for text in [
        "This means you have diabetes.",
        "You have iron deficiency anaemia.",
        "You are suffering from hypothyroidism.",
        "You are diagnosed with kidney disease.",
    ]:
        r = apply_guardrails(text)
        assert r.flagged, f"should have been flagged: {text!r}"


def test_safe_text_passes_through():
    text = (
        "Hemoglobin carries oxygen in your blood. A slightly low value can relate to "
        "reduced iron; eating iron-rich foods may help."
    )
    r = apply_guardrails(text)
    assert not r.flagged
    assert text.split(".")[0] in r.text
