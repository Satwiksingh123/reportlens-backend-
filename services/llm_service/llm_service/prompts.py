"""Prompt construction for biomarker explanation.

Design goals:
  - Constrain the model to *explain*, never *diagnose* or *prescribe*.
  - Force it to ground statements in the retrieved reference snippets (RAG), and to say
    "not enough information" rather than invent facts.
  - Keep output in simple, non-alarming language a layperson can act on.
"""

from dataclasses import dataclass

SYSTEM_PROMPT = """You are ReportLens, a careful health-literacy assistant that explains \
laboratory test results to non-medical people.

Rules you must always follow:
1. You EXPLAIN results. You never diagnose a disease, never name a specific condition the \
person "has", and never prescribe or recommend medication or dosages.
2. Ground every medical statement in the provided reference notes. If the notes do not \
cover something, say the information is limited rather than guessing.
3. Use plain, calm language. Avoid frightening wording. Do not overstate risk from a \
single value.
4. For any out-of-range value, briefly explain what the marker measures, what a low/high \
reading can generally relate to, and give evidence-based, non-drug lifestyle/diet \
suggestions when the reference notes support them.
5. Always remind the reader that only a qualified doctor can interpret results in context.
Return clear prose. Do not output JSON."""


@dataclass
class BiomarkerContext:
    test_name: str
    value: str | None
    unit: str | None
    reference_range: str | None
    status: str | None
    reference_notes: str = ""  # retrieved RAG snippets for this marker


def build_biomarker_prompt(ctx: BiomarkerContext) -> str:
    notes = ctx.reference_notes.strip() or "(no reference notes retrieved)"
    return f"""Explain this single lab result to the patient.

Test: {ctx.test_name}
Measured value: {ctx.value} {ctx.unit or ''}
Reference range: {ctx.reference_range or 'not provided'}
Status: {ctx.status or 'unknown'}

Reference notes (use ONLY these for medical claims):
{notes}

Write 2-4 short sentences. If the status is Low or High, include one practical, \
non-medication suggestion supported by the reference notes."""


def build_summary_prompt(explained: list[dict], abnormal_names: list[str]) -> str:
    lines = [f"- {e['test_name']}: {e['status']}" for e in explained]
    joined = "\n".join(lines)
    focus = (
        f"The values outside range are: {', '.join(abnormal_names)}."
        if abnormal_names
        else "All values are within their reference ranges."
    )
    return f"""Write a short, calm overall summary of this lab report for the patient.

Results:
{joined}

{focus}

Write 3-5 sentences. Do not diagnose. End by advising the reader to discuss the results \
with their doctor."""
