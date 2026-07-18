"""Adapter that runs the llm_service explainer over structured biomarkers.

Uses the self-hosted Ollama model when reachable; otherwise the llm_service falls back
to a safe deterministic explanation so the pipeline never blocks on model availability.
Explanations are grounded via the RAG retriever, which supplies curated reference notes
per biomarker.
"""

import sys
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

_SERVICES = Path(__file__).resolve().parents[3]


def _bootstrap(pkg: str) -> None:
    """Add a sibling service package to sys.path for an uninstalled checkout."""
    path = str(_SERVICES / pkg)
    if path not in sys.path:
        sys.path.insert(0, path)


try:
    from llm_service import explain_biomarkers
    from llm_service.ollama_client import OllamaClient
except ModuleNotFoundError:  # pragma: no cover - path bootstrap for uninstalled checkout
    _bootstrap("llm_service")
    from llm_service import explain_biomarkers
    from llm_service.ollama_client import OllamaClient

settings = get_settings()


@lru_cache(maxsize=1)
def _get_retriever():
    """Build the RAG retriever once (embeds the KB on first use). Returns None if the
    rag package is unavailable, so explanations degrade gracefully to ungrounded text."""
    try:
        from rag import build_default_retriever
    except ModuleNotFoundError:  # pragma: no cover - path bootstrap
        try:
            _bootstrap("rag")
            from rag import build_default_retriever
        except ModuleNotFoundError:
            return None
    return build_default_retriever()


def explain(rows: list[dict]) -> tuple[list[dict], str]:
    client = OllamaClient(base_url=settings.ollama_base_url, model=settings.ollama_model)
    return explain_biomarkers(rows, retriever=_get_retriever(), client=client)
