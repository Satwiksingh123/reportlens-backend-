"""Fine-tune TrOCR on synthetic lab-report lines.

Designed to run on a free Colab GPU. It (1) generates a synthetic dataset with the
data_synthesis package, (2) crops labelled lines into (image, text) pairs, (3) fine-tunes
`microsoft/trocr-small-printed`, and (4) reports Character Error Rate (CER) on a held-out
split before saving the model.

Run (in Colab, repo cloned):
    python -m ocr_engine.train_trocr --num-reports 800 --epochs 3 \
        --out ocr_engine/artifacts/trocr-lab

The heavy deps (torch/transformers/datasets/jiwer/accelerate) come from the `train` extra:
    pip install -e "services/ocr_engine[train]"
"""

import argparse
import sys
from pathlib import Path

# --- make the sibling data_synthesis package importable (repo checkout, no install) ---
_SERVICES = Path(__file__).resolve().parents[2]
for _pkg in ("data_synthesis",):
    _p = str(_SERVICES / _pkg)
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _generate_dataset(num_reports: int, data_dir: Path, seed: int) -> None:
    import json

    from data_synthesis.generator import generate_report, render_report

    data_dir.mkdir(parents=True, exist_ok=True)
    existing = len(list(data_dir.glob("*.png")))
    if existing >= num_reports:
        print(f"[data] reusing {existing} existing reports in {data_dir}")
        return
    print(f"[data] generating {num_reports} synthetic reports -> {data_dir}")
    for i in range(num_reports):
        report = generate_report(seed=seed + i)
        img, boxes = render_report(report, add_noise=True, seed=seed + i)
        stem = f"{i:06d}"
        img.save(data_dir / f"{stem}.png")
        (data_dir / f"{stem}.ocr.json").write_text(json.dumps(boxes))


def load_processor(model_dir: str):
    """Load a TrOCRProcessor, falling back to the slow tokenizer.

    Building TrOCR's *fast* tokenizer converts from the slow one, which needs
    sentencepiece/protobuf. When that conversion isn't possible we ask for the slow
    tokenizer directly instead of failing the whole run.
    """
    from transformers import TrOCRProcessor

    try:
        return TrOCRProcessor.from_pretrained(model_dir)
    except Exception as exc:  # noqa: BLE001 - any conversion failure -> try slow tokenizer
        print(f"[warn] fast tokenizer unavailable ({exc}); retrying with use_fast=False")

    try:
        return TrOCRProcessor.from_pretrained(model_dir, use_fast=False)
    except Exception as exc:  # noqa: BLE001
        # TrOCR's tokenizer is sentencepiece-based, so the slow path needs it too.
        raise RuntimeError(
            f"Could not load the TrOCR tokenizer for {model_dir!r}: {exc}\n"
            "This almost always means sentencepiece/protobuf are missing. Run:\n"
            "    pip install sentencepiece protobuf\n"
            "then restart the runtime (Colab: Runtime -> Restart session) and re-run."
        ) from exc


def _build_torch_dataset(samples, processor, max_target_length: int):
    import torch

    class LineDataset(torch.utils.data.Dataset):
        def __init__(self, items):
            self.items = items

        def __len__(self):
            return len(self.items)

        def __getitem__(self, idx):
            s = self.items[idx]
            pixel_values = processor(
                images=s.image.convert("RGB"), return_tensors="pt"
            ).pixel_values.squeeze(0)
            labels = processor.tokenizer(
                s.text,
                padding="max_length",
                max_length=max_target_length,
                truncation=True,
            ).input_ids
            labels = [tok if tok != processor.tokenizer.pad_token_id else -100 for tok in labels]
            return {"pixel_values": pixel_values, "labels": torch.tensor(labels)}

    return LineDataset(samples)


def main() -> None:
    ap = argparse.ArgumentParser(description="Fine-tune TrOCR on synthetic lab-report lines.")
    ap.add_argument("--num-reports", type=int, default=800)
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--base-model", type=str, default="microsoft/trocr-small-printed")
    ap.add_argument("--data-dir", type=str, default="ocr_engine/artifacts/synthetic")
    ap.add_argument("--out", type=str, default="ocr_engine/artifacts/trocr-lab")
    ap.add_argument("--max-target-length", type=int, default=64)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    import numpy as np
    from transformers import (
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
        VisionEncoderDecoderModel,
        default_data_collator,
    )

    from ocr_engine.dataset import build_line_samples, train_val_split

    data_dir = Path(args.data_dir)
    _generate_dataset(args.num_reports, data_dir, args.seed)

    print("[data] cropping labelled lines ...")
    samples = build_line_samples(data_dir)
    train_s, val_s = train_val_split(samples, val_ratio=0.1, seed=args.seed)
    print(f"[data] {len(train_s)} train / {len(val_s)} val line images")

    processor = load_processor(args.base_model)
    model = VisionEncoderDecoderModel.from_pretrained(args.base_model)

    # standard TrOCR fine-tuning config
    model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.vocab_size = model.config.decoder.vocab_size
    model.config.eos_token_id = processor.tokenizer.sep_token_id
    model.config.max_length = args.max_target_length
    model.config.num_beams = 4

    # Recent transformers generate from `generation_config`, NOT `model.config`. Its
    # default max_length is 20 tokens, which truncates every prediction and produces a
    # CER above 1.0 even while training loss looks fine. Set it explicitly.
    model.generation_config.max_length = args.max_target_length
    model.generation_config.num_beams = 4
    model.generation_config.decoder_start_token_id = processor.tokenizer.cls_token_id
    model.generation_config.eos_token_id = processor.tokenizer.sep_token_id
    model.generation_config.pad_token_id = processor.tokenizer.pad_token_id

    train_ds = _build_torch_dataset(train_s, processor, args.max_target_length)
    val_ds = _build_torch_dataset(val_s, processor, args.max_target_length)

    from jiwer import cer as jiwer_cer

    def compute_metrics(pred):
        labels_ids = pred.label_ids
        pred_ids = pred.predictions
        pred_str = processor.batch_decode(pred_ids, skip_special_tokens=True)
        labels_ids = np.where(labels_ids != -100, labels_ids, processor.tokenizer.pad_token_id)
        label_str = processor.batch_decode(labels_ids, skip_special_tokens=True)
        return {"cer": jiwer_cer(label_str, pred_str)}

    training_args = Seq2SeqTrainingArguments(
        predict_with_generate=True,
        generation_max_length=args.max_target_length,
        generation_num_beams=4,
        eval_strategy="epoch",
        save_strategy="epoch",
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        fp16=True,
        output_dir=args.out,
        logging_steps=25,
        save_total_limit=1,
        report_to=[],
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=default_data_collator,
        compute_metrics=compute_metrics,
    )

    print("[train] starting fine-tuning ...")
    trainer.train()

    metrics = trainer.evaluate()
    print(f"[eval] final CER = {metrics.get('eval_cer'):.4f}")

    out = Path(args.out)
    model.save_pretrained(out)
    processor.save_pretrained(out)
    print(f"[done] saved fine-tuned model + processor to {out.resolve()}")
    print("       Lower CER is better (0 = perfect). Zip this folder and use it for inference.")


if __name__ == "__main__":
    main()
