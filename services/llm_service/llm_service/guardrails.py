"""Post-generation safety guardrails.

Even a well-prompted model can drift into diagnosing or prescribing. This layer is a
deterministic backstop applied to every generated explanation:
  - guarantees the medical disclaimer is present,
  - flags (and can strip) sentences that diagnose a specific condition or recommend
    medication/dosage.

It is intentionally conservative: false positives (an over-cautious redaction) are far
safer here than false negatives.
"""

import re
from dataclasses import dataclass

DISCLAIMER = (
    "This is an educational explanation, not a medical diagnosis. "
    "Please consult a qualified doctor to interpret these results in your full context."
)

# Medication / dosage / prescription phrasing — unsafe, the whole sentence is dropped.
_PRESCRIPTIVE = re.compile(
    r"\b("
    r"take \d+\s*(?:mg|mcg|g|ml|tablet|tablets|pill|pills)"
    r"|\d+\s*mg\b"
    r"|prescrib(?:e|ing|ed)"
    r"|start (?:taking|on) (?:a|an|the)?\s*\w*(?:medication|medicine|drug|supplement)"
    r"|dosage|dose of"
    r")",
    re.IGNORECASE,
)

# Disease-attribution phrasing — softened ("may be associated with") rather than dropped,
# so the useful part of the sentence survives.
_DIAGNOSTIC = re.compile(
    r"\b(?:this (?:means|confirms) )?you (?:definitely )?"
    r"(?:have|are suffering from|are diagnosed with)\b",
    re.IGNORECASE,
)


@dataclass
class GuardrailResult:
    text: str
    flagged: list[str]  # human-readable reasons the input tripped a rule


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def apply_guardrails(text: str) -> GuardrailResult:
    flagged: list[str] = []
    kept: list[str] = []

    for sentence in _split_sentences(text):
        if _PRESCRIPTIVE.search(sentence):
            flagged.append(f"removed prescriptive/medication statement: {sentence!r}")
            continue  # drop the unsafe sentence entirely
        if _DIAGNOSTIC.search(sentence):
            flagged.append(f"softened diagnostic statement: {sentence!r}")
            sentence = _DIAGNOSTIC.sub("may be associated with", sentence)
        kept.append(sentence)

    cleaned = " ".join(kept).strip()
    if DISCLAIMER.lower() not in cleaned.lower():
        cleaned = f"{cleaned} {DISCLAIMER}".strip() if cleaned else DISCLAIMER

    return GuardrailResult(text=cleaned, flagged=flagged)
