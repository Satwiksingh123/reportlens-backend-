"""Fine-tune dataset construction (pure, no torch/GPU)."""

import json

from llm_service.finetune import (
    SEED_EXAMPLES,
    chat_record,
    record_from_biomarker,
    record_from_summary,
    to_jsonl,
)
from llm_service.prompts import SYSTEM_PROMPT, BiomarkerContext


def test_chat_record_shape():
    rec = chat_record("sys", "user", "assistant")
    roles = [m["role"] for m in rec["messages"]]
    assert roles == ["system", "user", "assistant"]
    assert rec["messages"][2]["content"] == "assistant"


def test_record_from_biomarker_uses_system_prompt_and_context():
    ctx = BiomarkerContext(
        test_name="Hemoglobin", value="10.4", unit="g/dL",
        reference_range="13.0-17.0", status="Low", reference_notes="notes",
    )
    rec = record_from_biomarker(ctx, "explained text")
    assert rec["messages"][0]["content"] == SYSTEM_PROMPT
    assert "Hemoglobin" in rec["messages"][1]["content"]
    assert rec["messages"][2]["content"] == "explained text"


def test_record_from_summary_lists_results():
    rec = record_from_summary(
        [{"test_name": "TSH", "status": "High"}], ["TSH"], "summary text"
    )
    assert "TSH" in rec["messages"][1]["content"]
    assert rec["messages"][2]["content"] == "summary text"


def test_to_jsonl_roundtrips():
    recs = [chat_record("s", "u", "a"), chat_record("s2", "u2", "a2")]
    lines = to_jsonl(recs).split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["messages"][1]["content"] == "u"


def test_seed_examples_are_safe_and_well_formed():
    assert len(SEED_EXAMPLES) >= 5
    banned = ["you have", "diagnosis is", "prescribe", "take this medication"]
    for rec in SEED_EXAMPLES:
        assert [m["role"] for m in rec["messages"]] == ["system", "user", "assistant"]
        answer = rec["messages"][2]["content"].lower()
        assert "doctor" in answer  # every answer defers to a clinician
        assert not any(b in answer for b in banned)
