# llm_service

Turns structured biomarkers into plain-language, **safety-constrained** explanations
using a self-hosted open-weight LLM (Ollama + Qwen2.5 / Llama 3.1). No third-party APIs.

## Components

- [`prompts.py`](llm_service/prompts.py) — a system prompt that constrains the model to
  *explain, never diagnose or prescribe*, and to ground claims in retrieved reference
  notes (RAG). Per-biomarker and overall-summary prompt builders.
- [`guardrails.py`](llm_service/guardrails.py) — a deterministic post-generation
  backstop: drops any sentence containing medication/dosage/prescription language,
  softens definitive disease-attribution ("you have X" → "may be associated with"), and
  guarantees the medical disclaimer is present. Conservative by design.
- [`ollama_client.py`](llm_service/ollama_client.py) — tiny HTTP client; raises
  `OllamaUnavailable` so callers can fall back.
- [`explainer.py`](llm_service/explainer.py) — orchestrates retrieve → prompt → model →
  guardrails, with a **safe deterministic fallback** when the model is unavailable (keeps
  CI and offline demos working).

## Usage

```python
from llm_service import explain_biomarkers
from llm_service.ollama_client import OllamaClient

rows = [{"test_name": "Hemoglobin", "value": "11.2", "unit": "g/dL",
         "reference_range": "13.0-17.0", "status": "Low"}]
enriched, summary = explain_biomarkers(rows, client=OllamaClient())
```

Pass a `retriever(test_name) -> notes` callable (from the RAG service) to ground
explanations in curated references.

## Test

```bash
pytest -q          # 10 tests (guardrails + explainer fallback)
ruff check .
```
