"""OllamaClient availability checks.

Uses a stubbed httpx.get so these run without a real Ollama server.
"""

import httpx
import pytest

from llm_service.ollama_client import OllamaClient


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _stub_get(monkeypatch, payload=None, exc=None):
    def fake_get(url, timeout=None):
        if exc is not None:
            raise exc
        return _Resp(payload)

    monkeypatch.setattr(httpx, "get", fake_get)


def test_available_when_model_present(monkeypatch):
    _stub_get(monkeypatch, {"models": [{"name": "qwen2.5:3b"}, {"name": "llama3.1:8b"}]})
    assert OllamaClient(model="qwen2.5:3b").is_available() is True


def test_untagged_config_matches_any_tag(monkeypatch):
    # A config value without a tag ("qwen2.5") should accept whatever tag is installed.
    _stub_get(monkeypatch, {"models": [{"name": "qwen2.5:3b"}]})
    assert OllamaClient(model="qwen2.5").is_available() is True


def test_unavailable_when_server_up_but_model_missing(monkeypatch):
    # The important case: a running server with the configured model NOT pulled must
    # report unavailable, so callers fall back once instead of failing per biomarker.
    _stub_get(monkeypatch, {"models": [{"name": "llama3.1:8b"}]})
    assert OllamaClient(model="qwen2.5:3b").is_available() is False


def test_unavailable_when_no_models_at_all(monkeypatch):
    _stub_get(monkeypatch, {"models": []})
    assert OllamaClient(model="qwen2.5:3b").is_available() is False


def test_unavailable_when_server_unreachable(monkeypatch):
    _stub_get(monkeypatch, exc=httpx.ConnectError("refused"))
    assert OllamaClient(model="qwen2.5:3b").is_available() is False


def test_unavailable_on_malformed_response(monkeypatch):
    def fake_get(url, timeout=None):
        class Bad(_Resp):
            def json(self):
                raise ValueError("not json")

        return Bad(None)

    monkeypatch.setattr(httpx, "get", fake_get)
    assert OllamaClient(model="qwen2.5:3b").is_available() is False


@pytest.mark.parametrize("bad", [{"models": [{}]}, {}])
def test_unavailable_on_unexpected_shapes(monkeypatch, bad):
    _stub_get(monkeypatch, bad)
    assert OllamaClient(model="qwen2.5:3b").is_available() is False
