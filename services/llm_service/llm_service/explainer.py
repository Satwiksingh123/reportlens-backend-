"""Orchestrates biomarker explanation: prompt -> model -> guardrails.

`retriever` is an optional callable(test_name) -> reference notes str, supplied by the
RAG service. When Ollama is unavailable, a deterministic template explanation is used so
the pipeline still produces safe, sensible output (useful for CI and offline demos).
"""

from collections.abc import Callable

from llm_service.guardrails import DISCLAIMER, apply_guardrails
from llm_service.ollama_client import OllamaClient, OllamaUnavailable
from llm_service.prompts import (
    SYSTEM_PROMPT,
    BiomarkerContext,
    build_biomarker_prompt,
    build_summary_prompt,
)

Retriever = Callable[[str], str]


def _fallback_explanation(ctx: BiomarkerContext) -> str:
    base = (
        f"{ctx.test_name} was measured at {ctx.value} {ctx.unit or ''}".strip()
        + f" (reference range {ctx.reference_range})."
        if ctx.reference_range
        else f"{ctx.test_name} was measured at {ctx.value} {ctx.unit or ''}.".strip()
    )
    follow_up = " discuss possible reasons and next steps with your doctor."
    if ctx.status == "High":
        tail = " This reading is above the reference range;" + follow_up
    elif ctx.status == "Low":
        tail = " This reading is below the reference range;" + follow_up
    else:
        tail = " This reading is within the reference range."
    return base + tail


def explain_biomarkers(
    rows: list[dict],
    retriever: Retriever | None = None,
    client: OllamaClient | None = None,
) -> tuple[list[dict], str]:
    """Return (rows_with_explanations, overall_summary).

    Each input row is a dict with test_name/value/unit/reference_range/status.
    """
    use_model = client is not None and client.is_available()
    enriched: list[dict] = []
    abnormal: list[str] = []

    for row in rows:
        notes = retriever(row["test_name"]) if retriever else ""
        ctx = BiomarkerContext(
            test_name=row["test_name"],
            value=row.get("value"),
            unit=row.get("unit"),
            reference_range=row.get("reference_range"),
            status=row.get("status"),
            reference_notes=notes,
        )
        if use_model:
            try:
                raw = client.generate(SYSTEM_PROMPT, build_biomarker_prompt(ctx))
            except OllamaUnavailable:
                raw = _fallback_explanation(ctx)
        else:
            raw = _fallback_explanation(ctx)

        guarded = apply_guardrails(raw)
        enriched.append(
            {
                **row,
                "explanation": guarded.text,
                "evidence": {"reference_notes": notes} if notes else None,
                "guardrail_flags": guarded.flagged or None,
            }
        )
        if row.get("status") in {"Low", "High"}:
            abnormal.append(row["test_name"])

    summary = _build_summary(enriched, abnormal, use_model, client)
    return enriched, summary


def _build_summary(
    enriched: list[dict], abnormal: list[str], use_model: bool, client: OllamaClient | None
) -> str:
    if use_model and client is not None:
        try:
            raw = client.generate(SYSTEM_PROMPT, build_summary_prompt(enriched, abnormal))
            return apply_guardrails(raw).text
        except OllamaUnavailable:
            pass
    if abnormal:
        body = (
            f"{len(abnormal)} value(s) fall outside the normal range: "
            f"{', '.join(abnormal)}."
        )
    else:
        body = "All measured values are within their reference ranges."
    return f"{body} {DISCLAIMER}"
