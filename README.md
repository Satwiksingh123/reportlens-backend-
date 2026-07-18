# ReportLens

ReportLens turns a lab report (PDF/scan/photo) into a plain-language, evidence-grounded
health summary — without sending any medical data to a third-party AI API. Every stage
of the pipeline (OCR, parsing, explanation) runs on self-hosted, open-source models.

> **Not a medical device.** ReportLens is an educational/informational tool. It does not
> diagnose, and every summary carries a "consult a doctor" disclaimer. See
> [`docs/safety.md`](docs/safety.md) once written.

## Architecture

```
Upload → OCR Engine → Medical Parser → RAG Retriever → Self-hosted LLM → Structured Summary
              │              │                │                │
        (fine-tuned)   (rules + NER)   (curated medical    (Ollama: Llama 3.1 / Qwen2.5,
                                         knowledge base)     + LoRA fine-tune)
```

Backed by an async pipeline: FastAPI accepts the upload, hands the job to a Celery
worker, and the worker walks the report through each service in turn.

## Services (monorepo)

| Service | Responsibility | Status |
|---|---|---|
| [`services/api`](services/api) | FastAPI backend: auth, uploads, report history, orchestration | working (async pipeline wired, parser integrated) |
| [`services/medical_parser`](services/medical_parser) | Rule engine + reference-range KB → structured `{test, value, unit, range, status}` | working (13 tests green) |
| [`services/data_synthesis`](services/data_synthesis) | Generates synthetic lab-report images (with ground truth) for training | working (5 tests green) |
| [`services/ocr_engine`](services/ocr_engine) | Fine-tuned OCR (docTR/PaddleOCR base) for report text + table extraction | planned (training scaffold) |
| [`services/rag`](services/rag) | Vector store over curated medical reference text, grounds LLM explanations | planned |
| [`services/llm_service`](services/llm_service) | Ollama-hosted LLM + prompt templates + LoRA fine-tuning pipeline | in progress |

## Supported report types (v1)

CBC, LFT, KFT/RFT, Lipid Profile, Thyroid Profile, Blood Sugar (Fasting/PP/HbA1c),
Vitamin D, Vitamin B12, Iron Profile, Uric Acid, Electrolytes, Urine Routine, Stool
Examination.

## Local development

```bash
cp .env.example .env
docker compose up -d postgres redis
cd services/api
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Full stack (once other services have code): `docker compose up --build`.

## Why these design choices

- **Synthetic training data, not scraped patient records** — real lab reports can't be
  legally/ethically collected for training. A synthetic generator produces unlimited
  labeled data with realistic scan noise instead.
- **RAG over a curated knowledge base** — grounds the LLM's medical explanations in
  actual reference text instead of letting it free-associate, and makes every claim
  traceable to a source.
- **Self-hosted open-weight LLM (Llama 3.1 / Qwen2.5)** — no patient data ever leaves
  the infrastructure you control, and no dependency on a proprietary API.
