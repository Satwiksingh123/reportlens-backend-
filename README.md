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
| [`services/medical_parser`](services/medical_parser) | Rule engine + reference-range KB → structured `{test, value, unit, range, status}` | working (46 tests green) |
| [`services/data_synthesis`](services/data_synthesis) | Generates synthetic lab-report images (with ground truth) for training | working (6 tests green) |
| [`services/ocr_engine`](services/ocr_engine) | Classical line segmentation + Tesseract recognition (default); optional from-scratch TrOCR fine-tuning pipeline | working (26 tests green) |
| [`services/rag`](services/rag) | Vector store over curated medical reference text, grounds LLM explanations | working (8 tests green, wired into pipeline) |
| [`services/llm_service`](services/llm_service) | Ollama-hosted LLM + prompts + safety guardrails + QLoRA fine-tuning (Colab) | working (27 tests green) |
| [`frontend`](frontend) | React + TypeScript SPA: auth, upload, live processing status, results | working |

## Supported report types (v1)

CBC, LFT, KFT/RFT, Lipid Profile, Thyroid Profile, Blood Sugar (Fasting/PP/HbA1c),
Vitamin D, Vitamin B12, Iron Profile, Uric Acid, Electrolytes, Urine Routine, Stool
Examination.

## Local development

### With Docker (the whole stack)

```bash
cp .env.example .env
docker compose up -d --build
```

That's it — the API is on http://localhost:8000 (docs at `/docs`). The `api` service runs
`alembic upgrade head` before uvicorn, so the schema is created on first start.

Services: `postgres`, `redis`, `ollama`, `api` (uvicorn), `worker` (Celery). Only the API
publishes a host port; Ollama is reachable to the other containers as `http://ollama:11434`
but deliberately not exposed to the host, so it can't collide with a locally installed Ollama.

For real LLM explanations, pull a model into the Ollama container once (it persists in the
`ollama_models` volume). Without it, explanations fall back to deterministic templates and
the pipeline still works end to end:

```bash
docker compose exec ollama ollama pull qwen2.5:3b
# then set OLLAMA_MODEL=qwen2.5:3b in .env and: docker compose up -d api worker
```

**Tight on disk?** The `ollama/ollama` image plus a pulled model needs several GB, which can
choke a host with only a few GB free (this was measured to hang the Docker Desktop VM
outright on a ~7GB-free machine — the pull died mid-transfer and the VM stopped responding
to anything, needing a full Docker Desktop restart to recover). If you already have Ollama
installed natively and running (`ollama serve`, with a model pulled), skip the `ollama`
service entirely and point the containers at the host instead:

```bash
# .env: OLLAMA_BASE_URL=http://host.docker.internal:11434
docker compose up -d postgres redis api worker   # omit "ollama" from the service list
```

`host.docker.internal` is how a container reaches the Windows/Mac host on Docker Desktop.
Verified working end-to-end this way: real PDF → OCR → parser → RAG → the host's Ollama →
guardrails → stored result, all through the actual Dockerized api/worker/postgres/redis.

Useful checks:

```bash
docker compose ps                 # health of each service
docker compose logs -f api        # or: worker
docker compose down              # stop (add -v to also drop the DB volume)
```

If you prefer running the app on the host and only its dependencies in Docker:

```bash
docker compose up -d postgres redis
cd services/api && pip install -r requirements.txt
alembic upgrade head && uvicorn app.main:app --reload
celery -A app.tasks.celery_app worker --loglevel=info   # second shell
```

### Without Docker (SQLite + background-thread pipeline)

For a quick run on a machine with no Docker/Postgres/Redis.

`PIPELINE_MODE` decides how an upload's processing runs:

| mode | what it does | use it for |
|---|---|---|
| `celery` (default) | dispatches to a Celery worker over Redis | production |
| `thread` | runs on a background thread inside the API process | local dev without Redis |
| `inline` | runs synchronously inside the upload request | tests |

Use `thread` for local development, **not** `inline`. Both avoid needing Redis, but `inline`
blocks the upload response until OCR *and* the LLM finish — tens of seconds to minutes — so
the browser sits on "Uploading…" and the app looks hung. `thread` returns `201` immediately
with status `uploaded`, and the frontend's normal poll-until-done flow shows live progress.

```bash
cd services/api
pip install -r requirements.txt

# OCR needs the tesseract binary:
#   Debian/Ubuntu: apt-get install tesseract-ocr
#   macOS:         brew install tesseract
#   Windows:       winget install UB-Mannheim.TesseractOCR

# Optional: real explanations instead of the deterministic fallback
ollama pull qwen2.5:3b   # ~2 GB, CPU-friendly

DATABASE_URL="sqlite:///./reportlens.db" alembic upgrade head

DATABASE_URL="sqlite:///./reportlens.db" \
PIPELINE_MODE=thread \
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

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at http://localhost:5173. See [`frontend/README.md`](frontend/README.md) for details.
The backend's default `CORS_ORIGINS` already allows that origin, so no extra config is
needed to run both side by side.

## Why these design choices

- **Synthetic training data, not scraped patient records** — real lab reports can't be
  legally/ethically collected for training. A synthetic generator produces unlimited
  labeled data with realistic scan noise instead.
- **RAG over a curated knowledge base** — grounds the LLM's medical explanations in
  actual reference text instead of letting it free-associate, and makes every claim
  traceable to a source.
- **Self-hosted open-weight LLM (Llama 3.1 / Qwen2.5)** — no patient data ever leaves
  the infrastructure you control, and no dependency on a proprietary API.
