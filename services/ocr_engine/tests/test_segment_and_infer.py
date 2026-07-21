"""Segmentation + inference assembly tests.

Self-contained: we draw a small multi-line image with PIL so this package's CI job does
not depend on data_synthesis. Recognition itself is covered with a StubRecognizer, so the
tests need no torch/model — they verify the layout + assembly logic.
"""

import json

from PIL import Image, ImageDraw

from ocr_engine import StubRecognizer, extract_text_from_image, segment_lines
from ocr_engine.dataset import build_line_samples, build_word_samples, train_val_split
from ocr_engine.infer import extract_text_from_pil
from ocr_engine.segment import split_into_words


def _font(size: int):
    """A real TrueType font so word/letter spacing is realistic. DejaVu ships on Linux CI;
    Arial on Windows. Falls back to the (thin) default only if neither is present."""
    from PIL import ImageFont

    for name in ("DejaVuSans.ttf", "Arial.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _make_page(lines: list[str], line_height: int = 40) -> Image.Image:
    """Render lines with a real 22px font and generous line spacing, approximating a
    scanned report closely enough to exercise line + word segmentation."""
    font = _font(22)
    img = Image.new("RGB", (700, 30 + line_height * len(lines)), "white")
    draw = ImageDraw.Draw(img)
    y = 15
    for text in lines:
        draw.text((15, y), text, fill="black", font=font)
        y += line_height
    return img


def test_segment_finds_expected_line_count():
    img = _make_page(["Hemoglobin 11.2", "WBC 11500", "Platelets 210000"])
    lines = segment_lines(img)
    assert len(lines) == 3
    # boxes are ordered top-to-bottom
    ys = [lb.box[1] for lb in lines]
    assert ys == sorted(ys)


def test_segment_ignores_blank_page():
    assert segment_lines(Image.new("RGB", (200, 200), "white")) == []


def test_segment_ignores_speckle_and_keeps_crops_tight():
    """Scattered speckle must not stretch a line crop to full page width (that crushes the
    text when TrOCR resizes to a square)."""
    import random

    from ocr_engine.segment import segment_lines as seg

    img = _make_page(["Hemoglobin 11.2"])
    px = img.load()
    w, h = img.size
    rng = random.Random(0)
    for _ in range(int(w * h * 0.001)):  # light grey dust across the whole page
        px[rng.randint(0, w - 1), rng.randint(0, h - 1)] = (150, 150, 150)
    lines = seg(img)
    assert len(lines) == 1
    # the crop must be far narrower than the page (text only), not full width
    assert lines[0].image.width < 0.6 * w


def test_pad_to_aspect_caps_ratio():
    from ocr_engine.preprocess import pad_to_aspect

    wide = Image.new("RGB", (600, 20), "white")  # aspect 30
    out = pad_to_aspect(wide, max_aspect=6.0)
    assert out.width / out.height <= 6.01
    # a already-square-ish crop is left alone
    ok = Image.new("RGB", (60, 20), "white")  # aspect 3
    assert pad_to_aspect(ok, max_aspect=6.0).size == (60, 20)


def test_split_into_words_splits_on_column_gaps():
    # report rows are column-aligned with wide gaps between fields
    img = _make_page(["Hemoglobin      11.2      gdL"])
    line = segment_lines(img)[0]
    words = split_into_words(line.image)
    assert len(words) == 3  # three columns


def test_extract_text_assembles_one_line_per_band():
    img = _make_page(["Alpha", "Beta", "Gamma"])
    text = extract_text_from_pil(img, StubRecognizer(token="X"))
    assert text.split("\n") == ["X", "X", "X"]


def test_extract_joins_words_within_a_line():
    # two columns -> two recognised crops joined by a space
    img = _make_page(["Sodium        141"])
    text = extract_text_from_pil(img, StubRecognizer(token="W"))
    assert text == "W W"


def test_build_word_samples_crops_each_word(tmp_path):
    img = _make_page(["TSH 3.1"])
    img.save(tmp_path / "000000.png")
    boxes = [{
        "text": "TSH 3.1",
        "box": [20, 15, 200, 40],
        "words": [
            {"text": "TSH", "box": [20, 15, 60, 40]},
            {"text": "3.1", "box": [90, 15, 130, 40]},
        ],
    }]
    (tmp_path / "000000.ocr.json").write_text(json.dumps(boxes))
    samples = build_word_samples(tmp_path)
    assert [s.text for s in samples] == ["TSH", "3.1"]
    assert all(s.image.width > 0 for s in samples)


def test_extract_from_image_path(tmp_path):
    img = _make_page(["One", "Two"])
    p = tmp_path / "page.png"
    img.save(p)
    text = extract_text_from_image(p, StubRecognizer(token="L"))
    assert text == "L\nL"


def test_missing_model_dir_raises_clear_error():
    """A path-like model dir that doesn't exist must not be mistaken for a Hub repo id
    (which fails with a confusing HTTP 401)."""
    import pytest

    from ocr_engine.recognizer import TrOCRRecognizer

    with pytest.raises(FileNotFoundError, match="Train it first"):
        TrOCRRecognizer(model_dir="artifacts/does-not-exist")


def test_build_line_samples_from_synthetic_layout(tmp_path):
    # emulate a data_synthesis sample: page png + <id>.ocr.json with boxes
    img = _make_page(["TSH 3.1", "Free T4 1.2"])
    (tmp_path / "000000.png")  # touch via save below
    img.save(tmp_path / "000000.png")
    # column-aligned text, as the synthetic generator emits it
    boxes = [{"text": "TSH          3.1", "box": [20, 15, 200, 40]},
             {"text": "Free T4      1.2", "box": [20, 45, 200, 70]}]
    (tmp_path / "000000.ocr.json").write_text(json.dumps(boxes))

    samples = build_line_samples(tmp_path)
    assert [s.text for s in samples] == ["TSH 3.1", "Free T4 1.2"]
    assert all("  " not in s.text for s in samples)  # column padding collapsed
    assert all(s.image.width > 0 and s.image.height > 0 for s in samples)

    train, val = train_val_split(samples, val_ratio=0.5, seed=1)
    assert len(train) + len(val) == 2
