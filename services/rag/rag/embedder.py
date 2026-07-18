"""Text embedders.

Two interchangeable backends:
  - HashingEmbedder: pure-numpy hashed bag-of-words with L2 normalisation. Deterministic,
    no downloads, works offline and in CI. Good enough for a small curated KB.
  - SentenceTransformerEmbedder: optional, higher-quality semantic embeddings for
    production (lazy import; requires the `semantic` extra).

Both return L2-normalised vectors so dot product == cosine similarity.
"""

import re
import zlib
from typing import Protocol

import numpy as np

_TOKEN = re.compile(r"[a-z0-9]+")


def _stable_hash(token: str) -> int:
    # zlib.crc32 is stable across processes (unlike built-in hash), so a persisted
    # index stays valid on reload.
    return zlib.crc32(token.encode("utf-8"))


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray:
        ...


def _l2_normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


class HashingEmbedder:
    """Hashing-trick bag-of-words embedding with unigrams + bigrams."""

    def __init__(self, dim: int = 512):
        self.dim = dim

    def _embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = _tokenize(text)
        grams = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False)]
        for g in grams:
            idx = _stable_hash(g) % self.dim
            vec[idx] += 1.0
        return vec

    def embed(self, texts: list[str]) -> np.ndarray:
        mat = np.vstack([self._embed_one(t) for t in texts]) if texts else np.zeros((0, self.dim))
        return _l2_normalize(mat)


class SentenceTransformerEmbedder:  # pragma: no cover - requires optional heavy dependency
    """Semantic embeddings via sentence-transformers (optional extra)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vecs = self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return vecs.astype(np.float32)
