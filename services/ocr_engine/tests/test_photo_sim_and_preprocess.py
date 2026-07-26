"""Phone-photo simulation and the preprocessing that undoes it.

These test measurable properties (skew is recovered, a lighting gradient is flattened,
degradation is deterministic per seed) rather than asserting on OCR output, which would
make them slow and environment-dependent.
"""

import numpy as np
import pytest
from PIL import Image, ImageDraw

from ocr_engine.photo_sim import PROFILES, degrade
from ocr_engine.preprocess import deskew, estimate_skew, flatten_lighting, prepare_photo


def _page(lines: int = 14) -> Image.Image:
    """A synthetic page of evenly-spaced dark text rows - enough structure for skew
    estimation to have something to lock onto."""
    img = Image.new("RGB", (900, 1200), "white")
    d = ImageDraw.Draw(img)
    y = 60
    for i in range(lines):
        d.rectangle([80, y, 820 - (i % 3) * 60, y + 18], fill="black")
        y += 78
    return img


def test_all_levels_produce_a_same_size_changed_image():
    src = _page()
    for level in PROFILES:
        out = degrade(src, level=level, seed=0)
        assert out.size == src.size
        assert out.mode == "RGB"
        diff = np.abs(
            np.asarray(out, dtype=np.int16) - np.asarray(src, dtype=np.int16)
        ).mean()
        assert diff > 1.0, f"{level} barely changed the image (mean diff {diff:.2f})"


def test_degradation_is_deterministic_per_seed():
    src = _page()
    a = degrade(src, level="moderate", seed=5)
    b = degrade(src, level="moderate", seed=5)
    c = degrade(src, level="moderate", seed=6)
    assert np.array_equal(np.asarray(a), np.asarray(b))
    assert not np.array_equal(np.asarray(a), np.asarray(c))


def test_harsher_levels_degrade_more():
    src = _page()

    def distance(level: str) -> float:
        out = degrade(src, level=level, seed=3)
        return float(
            np.abs(np.asarray(out, dtype=np.int16) - np.asarray(src, dtype=np.int16)).mean()
        )

    assert distance("light") < distance("harsh")


def test_unknown_level_rejected():
    with pytest.raises(ValueError, match="unknown level"):
        degrade(_page(), level="nonexistent")


def test_straight_page_reports_no_skew():
    assert abs(estimate_skew(_page())) < 0.4


@pytest.mark.parametrize("angle", [-4.0, -1.5, 2.0, 5.0])
def test_injected_rotation_is_recovered(angle):
    rotated = _page().rotate(angle, resample=Image.BICUBIC, fillcolor="white")
    # estimate_skew reports the correction needed, i.e. the opposite of the injected angle
    assert estimate_skew(rotated) == pytest.approx(-angle, abs=0.6)


def test_deskew_straightens_a_rotated_page():
    rotated = _page().rotate(3.5, resample=Image.BICUBIC, fillcolor="white")
    assert abs(estimate_skew(deskew(rotated))) < abs(estimate_skew(rotated))


def test_deskew_leaves_a_straight_page_alone():
    src = _page()
    assert deskew(src) is src


def test_flatten_lighting_evens_out_a_gradient():
    src = _page()
    arr = np.asarray(src, dtype=np.float32)
    # darken progressively left-to-right, as an off-centre light source would
    ramp = np.linspace(1.0, 0.45, arr.shape[1])[None, :, None]
    lit = Image.fromarray(np.clip(arr * ramp, 0, 255).astype(np.uint8))

    def paper_spread(img: Image.Image) -> float:
        """How much the *paper* brightness varies across the page.

        Uses a high per-column percentile as the paper level: robust to how much text a
        column contains, and (unlike a mask + mean) never empty for a column of pure paper.
        """
        g = np.asarray(img.convert("L"), dtype=np.float32)
        paper = np.percentile(g[:, ::40], 90, axis=0)
        return float(np.std(paper))

    assert paper_spread(flatten_lighting(lit)) < paper_spread(lit)


def test_prepare_photo_handles_a_degraded_page_end_to_end():
    out = prepare_photo(degrade(_page(), level="harsh", seed=11))
    assert out.size == _page().size
    assert abs(estimate_skew(out)) < 1.5
