"""Orchestrates biomarker explanation: prompt -> model -> guardrails.

`retriever` is an optional callable(test_name) -> reference notes str, supplied by the
RAG service.

WHY NOT ONE MODEL CALL PER BIOMARKER: it was, and a real full-body health check made the
cost obvious - 49 biomarkers x ~20-45s per call is over half an hour of the user watching a
spinner. Of those 49, 44 were within their reference ranges.

A normal result's explanation is genuinely formulaic ("X is A, measured at V, which sits
inside the reference range R"), and the interesting half of that sentence - what X actually
does - already exists as curated reference text in the RAG knowledge base. Generating it
with a model buys nothing and costs 20-45s each; asked to do 12 at once it also degrades
badly (measured: "Within normal range, but slightly low", repeated near-verbatim for
unrelated analytes).

So the model is spent where it earns its cost: results that fall outside their range, where
context and nuance genuinely matter. Everything in range gets a deterministic sentence built
from its measured value plus the curated note - instant, consistent, and impossible to
hallucinate. Same 49-biomarker report: ~35 minutes -> about a minute.
"""

import re
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

ABNORMAL_STATUSES = {"Low", "High"}


def _first_sentences(text: str, limit: int = 2) -> str:
    """First `limit` sentences of a reference note - enough to say what a marker is for
    without pasting a paragraph under every normal result.

    Strips the leading "[Source]" tag the knowledge base carries: it belongs in the evidence
    panel (where the source is shown deliberately), not mid-sentence in prose the patient
    reads.
    """
    text = re.sub(r"^\s*\[[^\]]+\]\s*", "", text)
    out: list[str] = []
    for chunk in text.replace("\n", " ").split(". "):
        chunk = chunk.strip()
        if not chunk:
            continue
        out.append(chunk if chunk.endswith(".") else chunk + ".")
        if len(out) >= limit:
            break
    return " ".join(out)


def _template_explanation(ctx: BiomarkerContext) -> str:
    """Deterministic explanation. Primary path for in-range results, and the safe fallback
    for anything else when no model is reachable."""
    measured = f"{ctx.test_name} was measured at {ctx.value} {ctx.unit or ''}".strip()
    base = (
        f"{measured} (reference range {ctx.reference_range})."
        if ctx.reference_range
        else f"{measured}."
    )

    follow_up = " discuss possible reasons and next steps with your doctor."
    if ctx.status == "High":
        tail = " This reading is above the reference range;" + follow_up
    elif ctx.status == "Low":
        tail = " This reading is below the reference range;" + follow_up
    else:
        tail = " This reading is within the reference range."

    # The curated note is what makes a templated explanation actually useful - it says what
    # the marker is for, which is the part a patient doesn't already know.
    context = _first_sentences(ctx.reference_notes) if ctx.reference_notes else ""
    return f"{base}{tail} {context}".strip()


# Kept as an alias: this is still exactly the "no model available" fallback.
_fallback_explanation = _template_explanation


def explain_biomarkers(
    rows: list[dict],
    retriever: Retriever | None = None,
    client: OllamaClient | None = None,
    explain_normal_with_model: bool = False,
) -> tuple[list[dict], str]:
    """Return (rows_with_explanations, overall_summary).

    Each input row is a dict with test_name/value/unit/reference_range/status.

    By default the model is only asked about results outside their reference range; in-range
    results get a deterministic explanation built from the value and the curated reference
    note. See the module docstring for the measurements behind that. Set
    explain_normal_with_model=True to send everything to the model - accept that a long
    panel then takes tens of minutes on CPU.
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
        is_abnormal = row.get("status") in ABNORMAL_STATUSES
        ask_model = use_model and (is_abnormal or explain_normal_with_model)

        if ask_model:
            try:
                raw = client.generate(SYSTEM_PROMPT, build_biomarker_prompt(ctx))
            except OllamaUnavailable:
                raw = _template_explanation(ctx)
        else:
            raw = _template_explanation(ctx)

        guarded = apply_guardrails(raw)
        enriched.append(
            {
                **row,
                "explanation": guarded.text,
                "evidence": {"reference_notes": notes} if notes else None,
                "guardrail_flags": guarded.flagged or None,
                # so the UI/tests can tell a generated explanation from a templated one
                "explained_by": "model" if ask_model else "template",
            }
        )
        if is_abnormal:
            abnormal.append(row["test_name"])

    summary = _build_summary(enriched, abnormal, use_model, client)
    return enriched, summary


NO_RESULTS_SUMMARY = (
    "No lab values could be read from this document, so there is nothing to explain. "
    "This usually means the upload wasn't a lab report, or the page was too blurred, "
    "cropped, or dark to read - try a clearer photo or the original PDF."
)


def _build_summary(
    enriched: list[dict], abnormal: list[str], use_model: bool, client: OllamaClient | None
) -> str:
    if not enriched:
        # Never let "nothing was read" become "everything looks normal". The old fallback
        # said "All measured values are within their reference ranges", which for a report
        # that produced ZERO values tells the user their results are fine when the system
        # never saw a single one. The model is deliberately not consulted here either -
        # asked to summarise an empty list, it has nothing to ground on and will invent.
        return f"{NO_RESULTS_SUMMARY} {DISCLAIMER}"

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
