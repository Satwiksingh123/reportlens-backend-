from rag.embedder import HashingEmbedder
from rag.knowledge_base import KNOWLEDGE_BASE
from rag.retriever import Retriever, build_default_retriever


def test_embedder_is_normalized_and_deterministic():
    emb = HashingEmbedder(dim=256)
    v1 = emb.embed(["hemoglobin carries oxygen"])
    v2 = emb.embed(["hemoglobin carries oxygen"])
    # L2-normalised -> unit length, and stable across calls (stable hash).
    assert abs(float((v1 * v1).sum()) - 1.0) < 1e-5
    assert (v1 == v2).all()


def test_retrieves_relevant_note_for_known_biomarker():
    r = build_default_retriever()
    notes = r.retrieve_notes("Hemoglobin")
    assert "oxygen" in notes.lower()
    assert notes.startswith("[")  # carries a source tag


def test_retriever_is_callable_matching_llm_interface():
    r = build_default_retriever()
    # explainer calls retriever(test_name) directly
    assert r("TSH") == r.retrieve_notes("TSH")
    assert "thyroid" in r("TSH").lower()


def test_unknown_term_below_floor_returns_empty():
    # A term unrelated to any KB doc should not force irrelevant grounding.
    r = Retriever(min_score=0.5)
    assert r.retrieve_notes("zzzz qqqq unrelated gibberish") == ""


# --- regressions found by running a REAL model (qwen2.5:3b) on a real electrolytes report ---


def test_no_cross_biomarker_note_contamination():
    """Every biomarker must get ITS OWN notes, never another biomarker's.

    Observed with pure vector similarity: "Magnesium" retrieved the *Bilirubin* note
    (score 0.31 - higher than correct matches like Sodium->Sodium at 0.22), because a
    hashing embedder scores raw character overlap. That fed the LLM confidently-wrong
    medical context. Exact canonical-name matching now takes priority over similarity.
    """
    r = build_default_retriever()
    checks = {
        "Magnesium": "magnesium",
        "Bicarbonate": "bicarbonate",
        "Calcium": "calcium",
        "Chloride": "chloride",
        "Sodium": "sodium",
        "Potassium": "potassium",
        "Phosphorus": "phosphorus",
        "Hemoglobin": "hemoglobin",
        "Creatinine": "creatinine",
        "TSH": "tsh",
    }
    for name, expected_word in checks.items():
        notes = r.retrieve_notes(name).lower()
        assert notes, f"{name} should have notes"
        assert expected_word in notes, f"{name} got the wrong biomarker's notes: {notes[:120]!r}"


def test_punctuated_canonical_name_still_matches_exactly():
    # The parser emits "Vitamin D (25-OH)"; the KB keys it the same way, and normalization
    # must make those match regardless of punctuation.
    r = build_default_retriever()
    assert "vitamin d" in r.retrieve_notes("Vitamin D (25-OH)").lower()


def test_out_of_scope_biomarker_gets_no_notes_rather_than_wrong_ones():
    # MPV / absolute counts are parsed on real reports but aren't in the KB. Returning
    # nothing is correct and safe; returning someone else's notes is not.
    r = build_default_retriever()
    assert r.retrieve_notes("MPV") == ""
    assert r.retrieve_notes("Absolute Neutrophil Count") == ""


def test_every_kb_doc_has_source_and_panel():
    for doc in KNOWLEDGE_BASE:
        assert doc.text.strip()
        assert doc.source.strip()
        assert doc.panel.strip()
