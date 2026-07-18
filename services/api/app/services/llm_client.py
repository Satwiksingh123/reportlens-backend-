"""Adapter that runs the llm_service explainer over structured biomarkers.

Uses the self-hosted Ollama model when reachable; otherwise the llm_service falls back
to a safe deterministic explanation so the pipeline never blocks on model availability.
A RAG retriever can be injected later to ground explanations in curated references.
"""

import sys
from pathlib import Path

from app.core.config import get_settings

try:
    from llm_service import explain_biomarkers
    from llm_service.ollama_client import OllamaClient
except ModuleNotFoundError:  # pragma: no cover - path bootstrap for uninstalled checkout
    _pkg = Path(__file__).resolve().parents[3] / "llm_service"
    sys.path.insert(0, str(_pkg))
    from llm_service import explain_biomarkers
    from llm_service.ollama_client import OllamaClient

settings = get_settings()


def explain(rows: list[dict]) -> tuple[list[dict], str]:
    client = OllamaClient(base_url=settings.ollama_base_url, model=settings.ollama_model)
    return explain_biomarkers(rows, retriever=None, client=client)
