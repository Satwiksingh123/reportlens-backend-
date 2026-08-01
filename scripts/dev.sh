#!/usr/bin/env bash
# Start ReportLens locally: API (background-thread pipeline, SQLite) + frontend.
#
# No Docker, no Postgres, no Redis. Ctrl-C stops both.
#
#   ./scripts/dev.sh
#
# Optional: have Ollama running with a model pulled (`ollama pull qwen2.5:3b`) for real
# explanations. Without it the pipeline still completes, using deterministic template text.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/services/api"
FRONTEND_DIR="$ROOT/frontend"
DB_PATH="${DB_PATH:-$API_DIR/reportlens_dev.db}"

# Pick the API's python: prefer its venv, fall back to whatever python is on PATH.
if [ -x "$API_DIR/.venv/Scripts/python.exe" ]; then      # Windows
  PY="$API_DIR/.venv/Scripts/python.exe"
elif [ -x "$API_DIR/.venv/bin/python" ]; then            # macOS / Linux
  PY="$API_DIR/.venv/bin/python"
else
  PY="$(command -v python3 || command -v python)"
  echo "note: no venv at services/api/.venv, using $PY"
fi

# The sibling service packages aren't pip-installed in a plain checkout. ':' on POSIX,
# ';' on Windows Python - get this wrong and imports fail with a confusing ModuleNotFound.
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) SEP=';' ;;
  *)                    SEP=':' ;;
esac
PKGS="$ROOT/services/medical_parser${SEP}$ROOT/services/rag${SEP}$ROOT/services/llm_service${SEP}$ROOT/services/ocr_engine"

export DATABASE_URL="sqlite:///$DB_PATH"
export PIPELINE_MODE=thread
export UPLOAD_DIR="${UPLOAD_DIR:-$API_DIR/uploads}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:3b}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:5173,http://127.0.0.1:5173}"
export PYTHONPATH="$PKGS"

echo "==> migrating $DB_PATH"
(cd "$API_DIR" && "$PY" -m alembic upgrade head)

echo "==> starting API on http://localhost:8000"
(cd "$API_DIR" && "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000) &
API_PID=$!

# Without this, Ctrl-C kills the script but leaves uvicorn holding port 8000, and the next
# run fails with a bind error that looks like the app is broken.
cleanup() {
  echo
  echo "==> stopping"
  kill "$API_PID" 2>/dev/null || true
  wait "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "==> installing frontend dependencies (first run)"
  (cd "$FRONTEND_DIR" && npm install)
fi

echo "==> starting frontend on http://localhost:5173"
(cd "$FRONTEND_DIR" && npm run dev)
