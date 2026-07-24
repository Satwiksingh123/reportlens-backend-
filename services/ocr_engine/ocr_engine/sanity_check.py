"""Run the full OCR pipeline on one freshly generated synthetic report.

Prints the ground-truth lines next to the recognised text so you can eyeball how well the
fine-tuned model is doing.

Deliberately a CLI (not notebook code): it runs in its own process, so it always picks up
the installed library versions rather than whatever a long-lived notebook kernel imported
earlier in the session.

    python -m ocr_engine.sanity_check --model-dir artifacts/trocr-lab
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


def main() -> None:
    ap = argparse.ArgumentParser(description="Full-pipeline sanity check on a synthetic page.")
    ap.add_argument("--model-dir", type=str, default="artifacts/trocr-lab")
    ap.add_argument("--seed", type=int, default=9999)
    args = ap.parse_args()

    from data_synthesis.generator import generate_report, render_report

    from ocr_engine.infer import extract_text_from_pil
    from ocr_engine.recognizer import TrOCRRecognizer

    report = generate_report(seed=args.seed)
    img, _ = render_report(report, add_noise=True, seed=args.seed)

    print("=== ground truth ===")
    for line in report.text_lines:
        if line.strip():
            print(line)

    recognizer = TrOCRRecognizer(model_dir=args.model_dir)

    # Self-diagnosing: prints exactly what decoding settings are active, so a stale
    # checkout (old code still on disk) is obvious from this output alone instead of
    # needing a separate round-trip to confirm.
    import inspect

    src = inspect.getsource(recognizer.recognize_batch)
    print("\n=== active generate() kwargs (from installed ocr_engine on disk) ===")
    for line in src.splitlines():
        if any(k in line for k in ("length_penalty", "early_stopping", "no_repeat", "min_new")):
            print(" ", line.strip())
    if "min_new_tokens" not in src:
        print("  !! min_new_tokens NOT found - this is a STALE checkout, re-run the clone "
              "cell (cell 2) to pull the latest fix, then re-run this cell.")

    print("\n=== OCR output ===")
    print(extract_text_from_pil(img, recognizer))


if __name__ == "__main__":
    main()
