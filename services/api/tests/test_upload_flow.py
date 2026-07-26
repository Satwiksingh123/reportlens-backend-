"""End-to-end HTTP flow: register -> login -> upload a report -> fetch results.

This is the test that was missing, and its absence let four separate runtime-only bugs
ship while the suite stayed green:
  - user registration 500'd (passlib incompatible with modern bcrypt),
  - the schema couldn't be created outside PostgreSQL (JSONB used directly),
  - .delay() built a broker connection even in eager mode,
  - Celery imported the redis result backend even in eager mode.
None of those are visible from unit tests of the individual pieces - only from actually
driving the API.

Runs against SQLite with the pipeline executed inline (no Redis/worker). The LLM is not
required: llm_service falls back to a deterministic template explanation when Ollama isn't
reachable, so this stays fast and hermetic in CI.
"""

import os
import sys
import uuid
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SERVICES = _REPO_ROOT / "services"


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """A TestClient wired to a throwaway SQLite DB with the pipeline running inline."""
    tmp = tmp_path_factory.mktemp("upload_flow")
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp / 'test.db'}"
    os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
    os.environ["UPLOAD_DIR"] = str(tmp / "uploads")

    # sibling service packages aren't installed in the api venv
    for pkg in ("medical_parser", "rag", "llm_service", "ocr_engine"):
        path = str(_SERVICES / pkg)
        if path not in sys.path:
            sys.path.insert(0, path)

    # settings are cached, and the app/engine read them at import time
    from app.core.config import get_settings

    get_settings.cache_clear()
    for mod in [m for m in list(sys.modules) if m.startswith("app.")]:
        del sys.modules[mod]

    from fastapi.testclient import TestClient

    import app.models  # noqa: F401  - registers tables on Base
    from app.core.database import Base, engine
    from app.main import app as fastapi_app

    Base.metadata.create_all(engine)
    yield TestClient(fastapi_app)

    get_settings.cache_clear()


@pytest.fixture(scope="module")
def auth_headers(client):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    password = "secret12345"
    assert client.post(
        "/api/auth/register", json={"email": email, "password": password}
    ).status_code == 201
    resp = client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_register_and_login_work(auth_headers):
    # The fixture asserting 201/200 IS the test - registration used to 500 outright.
    assert auth_headers["Authorization"].startswith("Bearer ")


def test_reports_require_authentication(client):
    assert client.get("/api/reports").status_code == 401


def test_upload_runs_the_pipeline_and_returns_structured_results(client, auth_headers):
    pdf = _REPO_ROOT / "sample_reports" / "providers" / "drlogy_vitb12.pdf"
    if not pdf.exists():
        pytest.skip(f"sample report not present: {pdf}")

    with pdf.open("rb") as f:
        resp = client.post(
            "/api/reports",
            headers=auth_headers,
            files={"file": (pdf.name, f, "application/pdf")},
        )
    assert resp.status_code == 201, resp.text
    report_id = resp.json()["id"]

    detail = client.get(f"/api/reports/{report_id}", headers=auth_headers)
    assert detail.status_code == 200
    data = detail.json()

    assert data["status"] == "completed", f"pipeline failed: {data.get('error_message')}"
    assert data["error_message"] is None
    assert data["summary"], "expected an overall summary"

    results = data["results"]
    assert results, "expected at least one parsed biomarker"
    for row in results:
        assert row["test_name"]
        assert row["explanation"], f"{row['test_name']} has no explanation"
        # every explanation must carry the safety disclaimer, model or fallback
        assert "consult a qualified doctor" in row["explanation"].lower()


def test_uploaded_report_appears_in_the_list(client, auth_headers):
    resp = client.get("/api/reports", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_unsupported_file_type_rejected(client, auth_headers):
    resp = client.post(
        "/api/reports",
        headers=auth_headers,
        files={"file": ("notes.txt", b"not a report", "text/plain")},
    )
    assert resp.status_code == 400
