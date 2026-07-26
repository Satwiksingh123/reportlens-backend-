"""Retriever: maps a biomarker/test name to grounded reference notes for the LLM.

An instance is callable — `retriever(test_name) -> str` — so it drops straight into
llm_service.explainer's `Retriever = Callable[[str], str]` contract.

Retrieval is name-first, similarity-second. The parser hands us *canonical* biomarker
names, and the knowledge base is keyed by exactly those names, so an exact name match is
authoritative and needs no scoring. Pure vector similarity is only a fallback, and a
deliberately strict one: with a hashing embedder, character-overlap can score an unrelated
document higher than the correct one ("Magnesium" scored 0.31 against the *Bilirubin* note
— above the score real correct matches like Sodium→Sodium got, 0.22). Returning wrong
reference notes is worse than returning none: it feeds the LLM confidently-wrong medical
context for the biomarker it is explaining.
"""

import re

from rag.embedder import Embedder, HashingEmbedder
from rag.index import VectorIndex
from rag.knowledge_base import KNOWLEDGE_BASE, KBDoc


def _normalize(name: str) -> str:
    """Lowercase, strip punctuation/extra spaces, so "Vitamin D (25-OH)" == "vitamin d 25 oh"."""
    return " ".join(re.findall(r"[a-z0-9]+", name.lower()))


class Retriever:
    def __init__(
        self,
        docs: list[KBDoc] | None = None,
        embedder: Embedder | None = None,
        top_k: int = 2,
        min_score: float = 0.5,
    ):
        self._embedder = embedder or HashingEmbedder()
        kb = docs if docs is not None else KNOWLEDGE_BASE
        self._index = VectorIndex(self._embedder)
        self._index.build(kb)
        self._top_k = top_k
        self._min_score = min_score
        # exact canonical-name lookup: normalized biomarker name -> its docs
        self._by_name: dict[str, list[KBDoc]] = {}
        for doc in kb:
            if doc.biomarker:
                self._by_name.setdefault(_normalize(doc.biomarker), []).append(doc)

    def _format(self, docs: list[KBDoc]) -> str:
        return " ".join(f"[{d.source}] {d.text}" for d in docs)

    def retrieve_notes(self, test_name: str) -> str:
        """Reference notes for a biomarker, or "" when we have nothing trustworthy.

        Exact canonical-name match wins; otherwise fall back to vector similarity above a
        strict floor. "" is a correct, safe answer - the explainer degrades to describing
        the value against its reference range without invented medical context.
        """
        exact = self._by_name.get(_normalize(test_name))
        if exact:
            return self._format(exact)

        hits = self._index.search(test_name, top_k=self._top_k)
        kept = [h.doc for h in hits if h.score >= self._min_score]
        return self._format(kept) if kept else ""

    # Makes the instance satisfy Callable[[str], str].
    def __call__(self, test_name: str) -> str:
        return self.retrieve_notes(test_name)


def build_default_retriever() -> Retriever:
    """Retriever over the bundled knowledge base using the offline hashing embedder."""
    return Retriever()
