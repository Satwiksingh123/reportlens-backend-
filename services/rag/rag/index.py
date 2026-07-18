"""In-memory cosine-similarity vector index.

Backed by a dense numpy matrix. For a small curated knowledge base (dozens to a few
hundred docs) a brute-force matmul is faster than it needs to be and has zero external
dependencies. Swap this class for a FAISS/Chroma index at the point the corpus grows to
tens of thousands of vectors — the retriever only depends on the `search` signature.
"""

from dataclasses import dataclass

import numpy as np

from rag.embedder import Embedder
from rag.knowledge_base import KBDoc


@dataclass
class SearchHit:
    doc: KBDoc
    score: float


class VectorIndex:
    def __init__(self, embedder: Embedder):
        self._embedder = embedder
        self._docs: list[KBDoc] = []
        self._matrix: np.ndarray = np.zeros((0, embedder.dim), dtype=np.float32)

    def build(self, docs: list[KBDoc]) -> None:
        self._docs = list(docs)
        # Embed the note text prefixed with the biomarker/panel so a name-only query still
        # lands on the right document.
        corpus = [f"{d.biomarker or d.panel}. {d.text}" for d in self._docs]
        self._matrix = self._embedder.embed(corpus)

    def search(self, query: str, top_k: int = 3) -> list[SearchHit]:
        if not self._docs:
            return []
        q = self._embedder.embed([query])  # (1, dim), already L2-normalised
        scores = (self._matrix @ q.T).ravel()  # cosine similarity
        k = min(top_k, len(self._docs))
        top_idx = np.argsort(-scores)[:k]
        return [SearchHit(self._docs[i], float(scores[i])) for i in top_idx]
