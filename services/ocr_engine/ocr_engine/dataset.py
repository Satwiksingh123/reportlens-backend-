"""Build a line-level recognition dataset from synthetic reports.

The data_synthesis package writes, per sample: `<id>.png` (page image) and `<id>.ocr.json`
(list of {"text", "box"} lines). Here we crop each labelled line into its own image and
pair it with the ground-truth text — exactly the (image -> text) supervision TrOCR needs.

Kept dependency-light (PIL only) so it is unit-testable without torch. The training script
converts these pairs into a HuggingFace Dataset.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass
class LineSample:
    image: Image.Image
    text: str


def _iter_sample_ids(data_dir: Path):
    for ocr_json in sorted(data_dir.glob("*.ocr.json")):
        stem = ocr_json.name[: -len(".ocr.json")]
        png = data_dir / f"{stem}.png"
        if png.exists():
            yield stem, png, ocr_json


def build_line_samples(data_dir: str | Path, pad: int = 2) -> list[LineSample]:
    """Crop every labelled line from every report into an (image, text) pair."""
    data_dir = Path(data_dir)
    samples: list[LineSample] = []
    for _stem, png, ocr_json in _iter_sample_ids(data_dir):
        page = Image.open(png).convert("RGB")
        w, h = page.size
        lines = json.loads(ocr_json.read_text())
        for line in lines:
            # Report rows are column-aligned with long runs of spaces. Exact space counts
            # are not recoverable from an image and would dominate the character error
            # rate, so collapse whitespace - downstream parsing splits on it anyway.
            text = " ".join((line.get("text") or "").split())
            if not text:
                continue
            x0, y0, x1, y1 = line["box"]
            crop = page.crop(
                (max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad))
            )
            samples.append(LineSample(image=crop, text=text))
    return samples


def build_word_samples(data_dir: str | Path, pad: int = 3) -> list[LineSample]:
    """Crop every labelled *word* into an (image, text) pair.

    Word crops stay near-square, which is TrOCR's sweet spot, so the recogniser learns far
    better than on whole lines squashed into a 384x384 square. Falls back to a line crop
    when a report predates per-word boxes.
    """
    data_dir = Path(data_dir)
    samples: list[LineSample] = []
    for _stem, png, ocr_json in _iter_sample_ids(data_dir):
        page = Image.open(png).convert("RGB")
        w, h = page.size
        lines = json.loads(ocr_json.read_text())
        for line in lines:
            words = line.get("words")
            if not words:  # backward compat: no per-word boxes -> use the line
                text = " ".join((line.get("text") or "").split())
                if text:
                    x0, y0, x1, y1 = line["box"]
                    samples.append(LineSample(_crop(page, x0, y0, x1, y1, pad, w, h), text))
                continue
            for word in words:
                text = (word.get("text") or "").strip()
                if not text:
                    continue
                x0, y0, x1, y1 = word["box"]
                samples.append(LineSample(_crop(page, x0, y0, x1, y1, pad, w, h), text))
    return samples


def _crop(page, x0, y0, x1, y1, pad, w, h):
    return page.crop((max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)))


def train_val_split(
    samples: list[LineSample], val_ratio: float = 0.1, seed: int = 0
) -> tuple[list[LineSample], list[LineSample]]:
    import random

    rng = random.Random(seed)
    idx = list(range(len(samples)))
    rng.shuffle(idx)
    n_val = max(1, int(len(samples) * val_ratio)) if samples else 0
    val_idx = set(idx[:n_val])
    train = [s for i, s in enumerate(samples) if i not in val_idx]
    val = [s for i, s in enumerate(samples) if i in val_idx]
    return train, val
