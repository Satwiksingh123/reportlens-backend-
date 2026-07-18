"""Segmentation + inference assembly tests.

Self-contained: we draw a small multi-line image with PIL so this package's CI job does
not depend on data_synthesis. Recognition itself is covered with a StubRecognizer, so the
tests need no torch/model — they verify the layout + assembly logic.
"""

import json

from PIL import Image, ImageDraw

from ocr_engine import StubRecognizer, extract_text_from_image, segment_lines
from ocr_engine.dataset import build_line_samples, train_val_split
from ocr_engine.infer import extract_text_from_pil


def _make_page(lines: list[str], line_height: int = 16, scale: int = 4) -> Image.Image:
    """Render lines with the (tiny) default PIL font, then upscale so strokes are thick
    and lines are tall — mimicking real report-scan text density, which the default
    bitmap font is too thin to produce on its own."""
    base = Image.new("RGB", (150, 16 + line_height * len(lines)), "white")
    draw = ImageDraw.Draw(base)
    y = 8
    for text in lines:
        draw.text((8, y), text, fill="black")
        y += line_height
    return base.resize((base.width * scale, base.height * scale), Image.NEAREST)


def test_segment_finds_expected_line_count():
    img = _make_page(["Hemoglobin 11.2", "WBC 11500", "Platelets 210000"])
    lines = segment_lines(img)
    assert len(lines) == 3
    # boxes are ordered top-to-bottom
    ys = [lb.box[1] for lb in lines]
    assert ys == sorted(ys)


def test_segment_ignores_blank_page():
    assert segment_lines(Image.new("RGB", (200, 200), "white")) == []


def test_extract_text_assembles_one_line_per_band():
    img = _make_page(["Alpha", "Beta", "Gamma"])
    text = extract_text_from_pil(img, StubRecognizer(token="X"))
    assert text.split("\n") == ["X", "X", "X"]


def test_extract_from_image_path(tmp_path):
    img = _make_page(["One", "Two"])
    p = tmp_path / "page.png"
    img.save(p)
    text = extract_text_from_image(p, StubRecognizer(token="L"))
    assert text == "L\nL"


def test_build_line_samples_from_synthetic_layout(tmp_path):
    # emulate a data_synthesis sample: page png + <id>.ocr.json with boxes
    img = _make_page(["TSH 3.1", "Free T4 1.2"])
    (tmp_path / "000000.png")  # touch via save below
    img.save(tmp_path / "000000.png")
    boxes = [{"text": "TSH 3.1", "box": [20, 15, 200, 40]},
             {"text": "Free T4 1.2", "box": [20, 45, 200, 70]}]
    (tmp_path / "000000.ocr.json").write_text(json.dumps(boxes))

    samples = build_line_samples(tmp_path)
    assert [s.text for s in samples] == ["TSH 3.1", "Free T4 1.2"]
    assert all(s.image.width > 0 and s.image.height > 0 for s in samples)

    train, val = train_val_split(samples, val_ratio=0.5, seed=1)
    assert len(train) + len(val) == 2
