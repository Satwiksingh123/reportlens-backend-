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
#
# Deliberately does NOT match a bare quantity like "9.00 mg/dL": lab results are quantities
# in mg-based units, so a bare "<number> mg" pattern deleted the very sentence stating the
# patient's own measured value (observed with a real model: "your calcium was measured at
# 9.00 mg/dL, within the normal range of 8.60 to 10.20 mg/dL" was dropped entirely).
# Dosage phrasing is matched by its verbs/nouns instead ("take 500 mg", "dose of 5 mg",
# "prescribe"), which is what actually signals a prescription.
_PRESCRIPTIVE = re.compile(
    r"\b("
    r"(?:take|taking|takes|consume|administer|inject|swallow)\s+"
    r"(?:\d+(?:\.\d+)?\s*(?:mg|mcg|g|iu|ml)\b|\d+\s*(?:tablet|tablets|pill|pills|capsule|capsules)\b)"
    r"|prescrib(?:e|es|ing|ed)"
    r"|start (?:taking|on) (?:a|an|the)?\s*\w*(?:medication|medicine|drug|supplement)"
    r"|dosage|dose of"
    r")",
    re.IGNORECASE,
)

# Disease-attribution phrasing — softened ("may be associated with") rather than dropped,
# so the useful part of the sentence survives.
#
# "you have" only counts as diagnostic when followed by something disease-like. A real model
# produced "so if you have any concerns, discuss them with your provider", which the old
# broader pattern rewrote into "so if may be associated with any concerns" - mangling a
# perfectly safe sentence. Requiring a condition-ish object (or an explicit
# suffering-from/diagnosed-with phrasing) keeps the rule aimed at actual diagnosis. Still
# deliberately conservative: an unrecognised condition word softens nothing, but the model
# is also prompt-constrained against diagnosing, and the disclaimer is always appended.
_CONDITION_HINT = (
    r"(?:a |an |the )?(?:mild |severe |chronic |acute )?"
    r"(?:\w+\s+)?(?:anaemia|anemia|diabetes|deficiency|disease|disorder|infection|"
    r"syndrome|failure|cancer|hypothyroidism|hyperthyroidism|condition)"
)
_DIAGNOSTIC = re.compile(
    r"\b(?:this (?:means|confirms) )?you (?:definitely )?"
    rf"(?:have\s+{_CONDITION_HINT}|are suffering from|are diagnosed with)\b",
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
