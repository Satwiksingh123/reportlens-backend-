"""Retriever: maps a biomarker/test name to grounded reference notes for the LLM.

An instance is callable — `retriever(test_name) -> str` — so it drops straight into
llm_service.explainer's `Retriever = Callable[[str], str]` contract.
"""

from rag.embedder import Embedder, HashingEmbedder
from rag.index import VectorIndex
from rag.knowledge_base import KNOWLEDGE_BASE, KBDoc


class Retriever:
    def __init__(
        self,
        docs: list[KBDoc] | None = None,
        embedder: Embedder | None = None,
        top_k: int = 2,
        min_score: float = 0.05,
    ):
        self._embedder = embedder or HashingEmbedder()
        self._index = VectorIndex(self._embedder)
        self._index.build(docs if docs is not None else KNOWLEDGE_BASE)
        self._top_k = top_k
        self._min_score = min_score

    def retrieve_notes(self, test_name: str) -> str:
        """Return concatenated reference notes for the closest KB docs, or "" if none clear
        the similarity floor (avoids grounding on irrelevant text)."""
        hits = self._index.search(test_name, top_k=self._top_k)
        kept = [h for h in hits if h.score >= self._min_score]
        if not kept:
            return ""
        return " ".join(f"[{h.doc.source}] {h.doc.text}" for h in kept)

    # Makes the instance satisfy Callable[[str], str].
    def __call__(self, test_name: str) -> str:
        return self.retrieve_notes(test_name)


def build_default_retriever() -> Retriever:
    """Retriever over the bundled knowledge base using the offline hashing embedder."""
    return Retriever()
