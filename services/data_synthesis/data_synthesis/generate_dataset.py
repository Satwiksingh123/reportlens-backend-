"""CLI: generate a synthetic lab-report dataset.

Usage:
    python -m data_synthesis.generate_dataset --count 500 --out data/synthetic/generated

Writes, per sample:
    <id>.png            rendered report image
    <id>.gt.json        ground truth: structured biomarkers + patient/lab metadata
    <id>.ocr.json       OCR supervision: text lines + bounding boxes
"""

import argparse
import json
from pathlib import Path

from data_synthesis.generator import generate_report, render_report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--out", type=str, default="data/synthetic/generated")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-noise", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for i in range(args.count):
        report = generate_report(seed=args.seed + i)
        img, boxes = render_report(report, add_noise=not args.no_noise, seed=args.seed + i)
        stem = f"{i:06d}"
        img.save(out / f"{stem}.png")
        (out / f"{stem}.gt.json").write_text(json.dumps(report.to_ground_truth(), indent=2))
        (out / f"{stem}.ocr.json").write_text(json.dumps(boxes, indent=2))

    print(f"Wrote {args.count} synthetic reports to {out.resolve()}")


if __name__ == "__main__":
    main()
