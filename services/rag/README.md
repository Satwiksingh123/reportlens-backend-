# rag

Retrieval-augmented grounding for ReportLens. Maps a biomarker name to curated,
source-tagged reference notes so the LLM explains results from evidence rather than
free-associating.

## How it works

```
test name ──▶ embed ──▶ cosine search over KB ──▶ top-k notes (score-filtered) ──▶ LLM
```

- **`knowledge_base.py`** — curated, non-diagnostic educational notes per biomarker,
  each tagged with the kind of public source it aligns with (MedlinePlus, WHO/ICMR).
- **`embedder.py`** — `HashingEmbedder` (pure-numpy, offline, deterministic) by default;
  `SentenceTransformerEmbedder` for production-quality semantic search (optional
  `semantic` extra).
- **`index.py`** — brute-force cosine `VectorIndex`. Swap for FAISS/Chroma once the
  corpus grows to tens of thousands of vectors; the retriever only needs `search`.
- **`retriever.py`** — `Retriever` is callable (`retriever(test_name) -> str`), matching
  `llm_service`'s `Retriever = Callable[[str], str]` contract, so it drops straight into
  the explainer. Below a similarity floor it returns `""` rather than forcing irrelevant
  grounding.

## Usage

```python
from rag import build_default_retriever

retrieve = build_default_retriever()
retrieve("Hemoglobin")   # -> "[MedlinePlus] Hemoglobin is the protein ..."
```

## Develop

```bash
pip install -e ".[dev]"      # add ".[dev,semantic]" for the semantic embedder
ruff check .
pytest -q
```

> Notes are written for an educational/portfolio tool and should be reviewed by a
> qualified clinician before any real-world use.
