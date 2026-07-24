"""Run the full OCR pipeline on one freshly generated synthetic report.

Prints the ground-truth lines next to the recognised text so you can eyeball accuracy, and
reports a character error rate (CER) over the whole page.

Defaults to the Tesseract engine (no GPU, no training). Pass --engine trocr --model-dir
<dir> to use the optional fine-tuned transformer instead.

    python -m ocr_engine.sanity_check                 # Tesseract (default)
    python -m ocr_engine.sanity_check --engine trocr --model-dir artifacts/trocr-lab
"""

import argparse
import sys
from pathlib import Path

# make the sibling data_synthesis package importable from a plain checkout
_SERVICES = Path(__file__).resolve().parents[2]
for _pkg in ("data_synthesis",):
    _p = str(_SERVICES / _pkg)
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _cer(ref: str, hyp: str) -> float:
    """Levenshtein distance / len(ref), a standard OCR character error rate."""
    r, h = ref, hyp
    prev = list(range(len(h) + 1))
    for i, rc in enumerate(r, 1):
        cur = [i]
        for j, hc in enumerate(h, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rc != hc)))
        prev = cur
    return prev[-1] / max(1, len(r))


def main() -> None:
    ap = argparse.ArgumentParser(description="Full-pipeline sanity check on a synthetic page.")
    ap.add_argument("--engine", choices=["tesseract", "trocr"], default="tesseract")
    ap.add_argument("--model-dir", type=str, default="artifacts/trocr-lab")
    ap.add_argument("--seed", type=int, default=9999)
    args = ap.parse_args()

    from data_synthesis.generator import generate_report, render_report

    from ocr_engine.infer import extract_text_from_pil

    report = generate_report(seed=args.seed)
    img, _ = render_report(report, add_noise=True, seed=args.seed)

    gt_lines = [ln for ln in report.text_lines if ln.strip()]
    print("=== ground truth ===")
    for line in gt_lines:
        print(line)

    if args.engine == "trocr":
        from ocr_engine.recognizer import TrOCRRecognizer

        recognizer = TrOCRRecognizer(model_dir=args.model_dir)
    else:
        from ocr_engine.recognizer import TesseractRecognizer

        recognizer = TesseractRecognizer()

    output = extract_text_from_pil(img, recognizer)
    print(f"\n=== OCR output ({args.engine}) ===")
    print(output)

    # CER on the collapsed-whitespace text (spacing between columns isn't what we grade).
    ref = " ".join(" ".join(gt_lines).split())
    hyp = " ".join(output.split())
    cer = _cer(ref, hyp)
    acc = max(0.0, 1 - cer) * 100
    print(f"\n=== accuracy ===\nCER = {cer:.3f}   (character accuracy ~ {acc:.1f}%)")


if __name__ == "__main__":
    main()
