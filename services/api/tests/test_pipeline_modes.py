"""The "thread" pipeline mode: upload returns immediately, work continues in background.

This mode exists because of a bug found by driving the real UI in a browser: with the
pipeline running inline, POST /api/reports blocked for the entire OCR + LLM run. The
frontend sat on "Uploading..." for over a minute with no feedback - indistinguishable from
a hung app, and the polling/progress UI never got a chance to render because navigation
only happens once the upload response arrives.

The contract these tests pin down:
  - the upload response comes back promptly, with status "uploaded" and no results yet,
  - the work really does happen afterwards, ending in a terminal status,
  - a failing report still reaches "failed" (a background thread must not swallow errors).
"""

import os
import sys
import time
import uuid
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SERVICES = _REPO_ROOT / "services"

TERMINAL = {"completed", "failed"}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("thread_mode")
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp / 'test.db'}"
    os.environ["PIPELINE_MODE"] = "thread"
    os.environ["UPLOAD_DIR"] = str(tmp / "uploads")

    for pkg in ("medical_parser", "rag", "llm_service", "ocr_engine"):
        path = str(_SERVICES / pkg)
        if path not in sys.path:
            sys.path.insert(0, path)

    from app.core.config import get_settings

    get_settings.cache_clear()
    for mod in [m for m in list(sys.modules) if m.startswith("app.")]:
        del sys.modules[mod]

    from fastapi.testclient import TestClient

    import app.models  # noqa: F401
    from app.core.database import Base, engine
    from app.main import app as fastapi_app

    Base.metadata.create_all(engine)
    yield TestClient(fastapi_app)

    get_settings.cache_clear()
    os.environ.pop("PIPELINE_MODE", None)


@pytest.fixture(scope="module")
def auth_headers(client):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={"email": email, "password": "secret12345"})
    resp = client.post(
        "/api/auth/login", data={"username": email, "password": "secret12345"}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _wait_for_terminal(client, headers, report_id, timeout=300):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = client.get(f"/api/reports/{report_id}", headers=headers).json()
        if last["status"] in TERMINAL:
            return last
        time.sleep(1)
    pytest.fail(f"report never reached a terminal status; last was {last!r}")


def test_upload_returns_immediately_and_finishes_in_background(client, auth_headers):
    pdf = _REPO_ROOT / "sample_reports" / "providers" / "drlogy_vitb12.pdf"
    if not pdf.exists():
        pytest.skip(f"sample report not present: {pdf}")

    started = time.monotonic()
    with pdf.open("rb") as f:
        resp = client.post(
            "/api/reports",
            headers=auth_headers,
            files={"file": (pdf.name, f, "application/pdf")},
        )
    elapsed = time.monotonic() - started

    assert resp.status_code == 201, resp.text
    body = resp.json()

    # The point of this mode: the response must not wait for OCR + the LLM. Ten seconds is
    # a deliberately loose ceiling (the real pipeline takes 30s-several minutes on CPU) so
    # the test fails only if the request is genuinely blocking on the work.
    assert elapsed < 10, f"upload blocked for {elapsed:.1f}s - it should return immediately"
    assert body["status"] == "uploaded"
    assert body["results"] == [], "results should not exist yet in thread mode"
    assert body["summary"] is None

    final = _wait_for_terminal(client, auth_headers, body["id"])
    assert final["status"] == "completed", f"pipeline failed: {final.get('error_message')}"
    assert final["results"], "background run produced no results"
    assert final["summary"]
    for row in final["results"]:
        assert "consult a qualified doctor" in (row["explanation"] or "").lower()


def test_background_failure_is_recorded_not_swallowed(client, auth_headers, monkeypatch):
    """A crash inside the background thread must land as status "failed" with a message -
    not leave the report stuck on "uploaded" forever with the user staring at a spinner."""
    pdf = _REPO_ROOT / "sample_reports" / "providers" / "drlogy_vitb12.pdf"
    if not pdf.exists():
        pytest.skip(f"sample report not present: {pdf}")

    import app.tasks.pipeline as pipeline

    monkeypatch.setattr(
        pipeline, "_run_ocr", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    with pdf.open("rb") as f:
        resp = client.post(
            "/api/reports",
            headers=auth_headers,
            files={"file": (pdf.name, f, "application/pdf")},
        )
    assert resp.status_code == 201

    final = _wait_for_terminal(client, auth_headers, resp.json()["id"], timeout=60)
    assert final["status"] == "failed"
    assert "boom" in (final["error_message"] or "")
