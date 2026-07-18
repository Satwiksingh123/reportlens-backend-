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


def test_every_kb_doc_has_source_and_panel():
    for doc in KNOWLEDGE_BASE:
        assert doc.text.strip()
        assert doc.source.strip()
        assert doc.panel.strip()
