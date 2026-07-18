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

## Fine-tuning the explainer (LoRA, optional — Colab GPU)

The base model works out of the box. To specialise it in the ReportLens style + safety
envelope, there's a QLoRA pipeline under [`llm_service/finetune`](llm_service/finetune):

- [`dataset.py`](llm_service/finetune/dataset.py) — chat-format records + hand-written,
  safety-checked seed exemplars (pure, unit-tested).
- [`build_dataset.py`](llm_service/finetune/build_dataset.py) — synthetic report →
  parser → RAG-grounded teacher → `explainer_sft.jsonl`.
- [`train_lora.py`](llm_service/finetune/train_lora.py) — Unsloth 4-bit QLoRA on
  Qwen2.5-3B, then **GGUF export for Ollama** (stays self-hosted, no external API).

**How to run (no coding):** open
[`notebooks/train_lora_colab.ipynb`](notebooks/train_lora_colab.ipynb) in Google Colab,
set a T4 GPU runtime, and *Run all*. It clones the repo, builds the dataset, fine-tunes,
does a sample generation, and downloads the GGUF. Then on your machine:

```bash
ollama create reportlens-explainer -f explainer-lora-gguf/Modelfile
# API .env:  OLLAMA_MODEL=reportlens-explainer
```

> The teacher is the deterministic RAG+template explainer, so the LoRA primarily learns
> ReportLens's *format and safety behaviour*. Swap in a stronger teacher to raise answer
> quality — the pipeline and record format don't change.

## Test

```bash
pytest -q          # 15 tests (guardrails + explainer fallback + finetune dataset)
ruff check .
```
