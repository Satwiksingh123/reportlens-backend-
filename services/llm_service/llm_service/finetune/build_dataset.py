"""Generate the instruction-tuning JSONL for the explainer LoRA.

Pipeline (mirrors the real product): synthetic report -> medical_parser -> RAG-grounded
explainer (teacher, no Ollama needed) -> chat records. Combined with the hand-written
SEED_EXAMPLES, this is the training set.

Run (repo cloned; siblings on path handled below):
    python -m llm_service.finetune.build_dataset --num-reports 300 \
        --out llm_service/artifacts/explainer_sft.jsonl

The teacher here is the deterministic RAG+template explainer, so the LoRA learns the
ReportLens *format and safety envelope*. Swap in a stronger teacher (e.g. a large local
model) to raise answer quality — the record format is unchanged.
"""

import argparse
import sys
from pathlib import Path

# make sibling service packages importable from a plain checkout
_SERVICES = Path(__file__).resolve().parents[3]
for _pkg in ("data_synthesis", "medical_parser", "rag"):
    _p = str(_SERVICES / _pkg)
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _build_records(num_reports: int, seed: int) -> list[dict]:
    from data_synthesis.generator import generate_report
    from medical_parser import parse_report

    from llm_service.explainer import explain_biomarkers
    from llm_service.finetune.dataset import (
        SEED_EXAMPLES,
        record_from_biomarker,
        record_from_summary,
    )
    from llm_service.prompts import BiomarkerContext

    try:
        from rag import build_default_retriever

        retriever = build_default_retriever()
    except ModuleNotFoundError:
        retriever = None

    records: list[dict] = list(SEED_EXAMPLES)

    for i in range(num_reports):
        report = generate_report(seed=seed + i)
        # render the plain-text lines the parser expects
        text = "\n".join(report.text_lines)
        rows = [b.to_dict() for b in parse_report(text, sex=report.patient_sex)]
        if not rows:
            continue

        enriched, summary = explain_biomarkers(rows, retriever=retriever, client=None)
        abnormal = [r["test_name"] for r in enriched if r.get("status") in {"Low", "High"}]

        for r in enriched:
            ctx = BiomarkerContext(
                test_name=r["test_name"],
                value=r.get("value"),
                unit=r.get("unit"),
                reference_range=r.get("reference_range"),
                status=r.get("status"),
                reference_notes=(r.get("evidence") or {}).get("reference_notes", ""),
            )
            records.append(record_from_biomarker(ctx, r["explanation"]))

        records.append(record_from_summary(enriched, abnormal, summary))

    return records


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--num-reports", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=str, default="llm_service/artifacts/explainer_sft.jsonl")
    args = ap.parse_args()

    from llm_service.finetune.dataset import to_jsonl

    records = _build_records(args.num_reports, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_jsonl(records), encoding="utf-8")
    print(f"[done] wrote {len(records)} training records to {out.resolve()}")


if __name__ == "__main__":
    main()
