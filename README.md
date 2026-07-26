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
| [`services/ocr_engine`](services/ocr_engine) | Classical line segmentation + Tesseract recognition (default); optional from-scratch TrOCR fine-tuning pipeline | working (11 tests green) |
| [`services/rag`](services/rag) | Vector store over curated medical reference text, grounds LLM explanations | working (5 tests green, wired into pipeline) |
| [`services/llm_service`](services/llm_service) | Ollama-hosted LLM + prompts + safety guardrails + QLoRA fine-tuning (Colab) | working (15 tests green) |

## Supported report types (v1)

CBC, LFT, KFT/RFT, Lipid Profile, Thyroid Profile, Blood Sugar (Fasting/PP/HbA1c),
Vitamin D, Vitamin B12, Iron Profile, Uric Acid, Electrolytes, Urine Routine, Stool
Examination.

## Local development

### With Docker (Postgres + Redis + a Celery worker)

```bash
cp .env.example .env
docker compose up -d postgres redis
cd services/api
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
# in a second shell:
celery -A app.tasks.celery_app worker --loglevel=info
```

Full stack: `docker compose up --build`.

### Without Docker (SQLite + in-process pipeline)

For a quick run on a machine with no Docker/Postgres/Redis. `CELERY_TASK_ALWAYS_EAGER`
runs the pipeline inline in the upload request instead of dispatching to a worker, so no
broker is needed — the upload call blocks until OCR + parsing + explanation finish. Dev
only; never enable it in production.

```bash
cd services/api
pip install -r requirements.txt

# OCR needs the tesseract binary:
#   Debian/Ubuntu: apt-get install tesseract-ocr
#   macOS:         brew install tesseract
#   Windows:       winget install UB-Mannheim.TesseractOCR

# Optional: real explanations instead of the deterministic fallback
ollama pull qwen2.5:3b   # ~2 GB, CPU-friendly

DATABASE_URL="sqlite:///./reportlens.db" \
CELERY_TASK_ALWAYS_EAGER=true \
UPLOAD_DIR=./uploads \
OLLAMA_MODEL=qwen2.5:3b \
PYTHONPATH="../medical_parser:../rag:../llm_service:../ocr_engine" \
uvicorn app.main:app --reload
```

Then, from another shell:

```bash
curl -s -X POST localhost:8000/api/auth/register \
  -H 'content-type: application/json' \
  -d '{"email":"you@example.com","password":"secret12345"}'

TOKEN=$(curl -s -X POST localhost:8000/api/auth/login \
  -d 'username=you@example.com&password=secret12345' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s -X POST localhost:8000/api/reports -H "Authorization: Bearer $TOKEN" \
  -F 'file=@../../sample_reports/providers/drlogy_vitb12.pdf;type=application/pdf'

curl -s localhost:8000/api/reports/1 -H "Authorization: Bearer $TOKEN"
```

Without Ollama the pipeline still works — `llm_service` falls back to a deterministic
template explanation, so the flow is testable offline. On CPU, expect roughly 10–30 s per
biomarker with a real model (no GPU here); the fallback is instant.

## Why these design choices

- **Synthetic training data, not scraped patient records** — real lab reports can't be
  legally/ethically collected for training. A synthetic generator produces unlimited
  labeled data with realistic scan noise instead.
- **RAG over a curated knowledge base** — grounds the LLM's medical explanations in
  actual reference text instead of letting it free-associate, and makes every claim
  traceable to a source.
- **Self-hosted open-weight LLM (Llama 3.1 / Qwen2.5)** — no patient data ever leaves
  the infrastructure you control, and no dependency on a proprietary API.
