"""Instruction-tuning dataset for the ReportLens explainer LoRA.

Produces chat-format records ({"messages": [system, user, assistant]}) that teach a base
instruct model the ReportLens *style and safety envelope*: explain-don't-diagnose, ground
claims in reference notes, calm plain language, always defer to a doctor.

Two sources feed the dataset:
  - SEED_EXAMPLES: a small, hand-written, high-quality set (the quality anchor).
  - programmatic examples built by build_dataset.py from synthetic reports, using the
    current RAG-grounded explainer as a teacher (the volume + format anchor).

This module is pure/data-only so it is unit-testable without torch or the sibling
packages. The heavy generation lives in build_dataset.py.
"""

import json

from llm_service.prompts import (
    SYSTEM_PROMPT,
    BiomarkerContext,
    build_biomarker_prompt,
    build_summary_prompt,
)

ChatRecord = dict


def chat_record(system: str, user: str, assistant: str) -> ChatRecord:
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ]
    }


def record_from_biomarker(ctx: BiomarkerContext, assistant_text: str) -> ChatRecord:
    """Build a training record for a single biomarker from its context + target text."""
    return chat_record(SYSTEM_PROMPT, build_biomarker_prompt(ctx), assistant_text)


def record_from_summary(
    explained: list[dict], abnormal_names: list[str], assistant_text: str
) -> ChatRecord:
    return chat_record(
        SYSTEM_PROMPT, build_summary_prompt(explained, abnormal_names), assistant_text
    )


def to_jsonl(records: list[ChatRecord]) -> str:
    """Serialise records to JSONL (one JSON object per line)."""
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in records)


# ---------------------------------------------------------------------------
# Hand-written quality anchors. Each is safe (no diagnosis/prescription), grounded, calm,
# and ends by deferring to a doctor — the behaviour we want the LoRA to imitate.
# ---------------------------------------------------------------------------

SEED_EXAMPLES: list[ChatRecord] = [
    record_from_biomarker(
        BiomarkerContext(
            test_name="Hemoglobin",
            value="10.4",
            unit="g/dL",
            reference_range="13.0-17.0",
            status="Low",
            reference_notes=(
                "[MedlinePlus] Hemoglobin is the protein in red blood cells that carries "
                "oxygen. A low level is called anaemia and can relate to low iron, vitamin "
                "B12 or folate, blood loss, or long-term illness. Iron-rich foods such as "
                "leafy greens and legumes can support healthy levels."
            ),
        ),
        "Hemoglobin is the protein in your red blood cells that carries oxygen around your "
        "body. Your result of 10.4 g/dL is a little below the usual range of 13.0–17.0, "
        "which is generally described as mild anaemia. This can relate to things like low "
        "iron or certain vitamins, so including more iron-rich foods such as leafy greens "
        "and legumes may help. A doctor can check the cause and advise what, if anything, "
        "you need to do.",
    ),
    record_from_biomarker(
        BiomarkerContext(
            test_name="TSH",
            value="6.8",
            unit="uIU/mL",
            reference_range="0.4-4.0",
            status="High",
            reference_notes=(
                "[MedlinePlus] TSH is the pituitary hormone that signals the thyroid. A "
                "high TSH usually suggests an underactive thyroid and is interpreted with "
                "T3/T4 and symptoms."
            ),
        ),
        "TSH is a hormone your body uses to signal your thyroid gland. Your value of 6.8 is "
        "above the usual range of 0.4–4.0, which can be a sign that the thyroid is working "
        "a little slower than expected. This is usually looked at together with other "
        "thyroid tests and how you feel, rather than on its own. It's best to share this "
        "result with your doctor, who can decide whether any follow-up is needed.",
    ),
    record_from_biomarker(
        BiomarkerContext(
            test_name="LDL Cholesterol",
            value="168",
            unit="mg/dL",
            reference_range="<100",
            status="High",
            reference_notes=(
                "[WHO] LDL is often called 'bad' cholesterol because higher levels are "
                "associated with build-up in arteries over time. Diets lower in saturated "
                "and trans fats, higher in fibre, and regular physical activity support "
                "healthier LDL levels."
            ),
        ),
        "LDL is sometimes called 'bad' cholesterol because higher levels are linked, over "
        "time, with build-up in the arteries. Your result of 168 mg/dL is above the "
        "suggested target of under 100. Choices like eating less saturated and fried food, "
        "adding more fibre, and staying physically active are well-established ways to help "
        "bring it down. Your doctor can look at this alongside your other heart-health "
        "factors and guide next steps.",
    ),
    record_from_biomarker(
        BiomarkerContext(
            test_name="Vitamin D (25-OH)",
            value="14",
            unit="ng/mL",
            reference_range="30-100",
            status="Low",
            reference_notes=(
                "[MedlinePlus] Vitamin D supports bone health and immune function. Low "
                "levels are very common and can relate to limited sun exposure and low "
                "dietary intake. Safe sunlight, fortified foods, and supplementation when "
                "advised can help restore levels."
            ),
        ),
        "Vitamin D helps keep your bones strong and supports your immune system. Your level "
        "of 14 ng/mL is below the usual range of 30–100, which is a very common finding. It "
        "often relates to limited sunlight and diet. Safe sun exposure and vitamin-D-rich or "
        "fortified foods can help, and a doctor may suggest a supplement if it's right for "
        "you. It's worth discussing the result with them.",
    ),
    record_from_biomarker(
        BiomarkerContext(
            test_name="Fasting Blood Sugar",
            value="92",
            unit="mg/dL",
            reference_range="70-100",
            status="Normal",
            reference_notes=(
                "[WHO] Fasting blood sugar is measured after not eating for several hours. "
                "A balanced diet, weight management, and activity support healthy glucose."
            ),
        ),
        "Fasting blood sugar is your blood glucose measured after not eating for several "
        "hours. Your result of 92 mg/dL sits comfortably within the usual range of 70–100, "
        "which is reassuring. Continuing balanced meals and regular activity helps keep it "
        "there. As always, your doctor can interpret this alongside the rest of your report.",
    ),
    record_from_summary(
        explained=[
            {"test_name": "Hemoglobin", "status": "Low"},
            {"test_name": "WBC Count", "status": "Normal"},
            {"test_name": "Platelet Count", "status": "Normal"},
        ],
        abnormal_names=["Hemoglobin"],
        assistant_text=(
            "Overall, most of your blood count results are within their normal ranges, "
            "which is reassuring. The main value to note is a slightly low hemoglobin, "
            "which can relate to things like iron levels and is common and often "
            "manageable. Your white cells and platelets look normal. None of this is a "
            "diagnosis on its own. Please go through these results with your doctor, who "
            "can see the full picture and advise on anything that may need attention."
        ),
    ),
]
