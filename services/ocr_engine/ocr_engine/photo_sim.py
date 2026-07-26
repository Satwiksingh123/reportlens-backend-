"""Simulate a phone-photographed / scanned report from a clean page image.

Real users photograph reports with a phone rather than uploading the lab's original PDF,
and that path was entirely untested - all accuracy numbers so far are on clean digital
PDFs. This applies the degradations a phone photo actually introduces, so the drop can be
measured and preprocessing can be evaluated against something reproducible.

HONEST LIMITATION: a simulation is not a real photo. It covers geometry (rotation,
perspective), optics (blur), sensor/codec noise (JPEG, grain) and lighting (gradient,
shadow), which is what OCR is sensitive to - but a real phone adds effects not modelled
here (rolling shutter, screen glare, motion streaks, auto-enhancement). Treat results as
a lower bound that is directionally useful, not as a substitute for real photos.

    from ocr_engine.photo_sim import degrade
    photo = degrade(clean_page_image, level="moderate", seed=0)
"""

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


@dataclass(frozen=True)
class DegradeProfile:
    """How aggressively to degrade. Values are ranges sampled per-call."""

    rotation_deg: float  # max absolute rotation
    perspective: float  # max corner displacement as a fraction of width
    blur_radius: float  # max gaussian blur radius
    jpeg_quality: int  # JPEG quality to round-trip through
    noise_sigma: float  # gaussian pixel noise std-dev (0-255 scale)
    lighting: float  # 0 = even, 1 = strong gradient across the page
    contrast: float  # multiplier (<1 washes the page out)


# "light" ~ a careful, well-lit photo held straight; "harsh" ~ a hurried handheld shot in
# poor indoor light. Values chosen to look plausible by eye rather than fitted to data.
PROFILES: dict[str, DegradeProfile] = {
    "light": DegradeProfile(
        rotation_deg=1.0, perspective=0.004, blur_radius=0.6,
        jpeg_quality=85, noise_sigma=2.0, lighting=0.15, contrast=0.97,
    ),
    "moderate": DegradeProfile(
        rotation_deg=2.5, perspective=0.012, blur_radius=1.1,
        jpeg_quality=70, noise_sigma=4.0, lighting=0.35, contrast=0.92,
    ),
    "harsh": DegradeProfile(
        rotation_deg=5.0, perspective=0.025, blur_radius=1.8,
        jpeg_quality=50, noise_sigma=7.0, lighting=0.55, contrast=0.85,
    ),
}


def _perspective_warp(img: Image.Image, strength: float, rng: np.random.Generator):
    """Nudge the four corners independently - a page photographed at a slight angle."""
    w, h = img.size
    d = strength * w
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    dst = [
        (rng.uniform(0, d), rng.uniform(0, d)),
        (w - rng.uniform(0, d), rng.uniform(0, d)),
        (w - rng.uniform(0, d), h - rng.uniform(0, d)),
        (rng.uniform(0, d), h - rng.uniform(0, d)),
    ]
    # solve for the 8 perspective coefficients mapping dst -> src (PIL samples backwards)
    matrix = []
    for (dx, dy), (sx, sy) in zip(dst, src, strict=True):
        matrix.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy])
        matrix.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy])
    a = np.array(matrix, dtype=np.float64)
    b = np.array(src, dtype=np.float64).reshape(8)
    coeffs = np.linalg.solve(a, b)
    return img.transform((w, h), Image.PERSPECTIVE, tuple(coeffs),
                         resample=Image.BICUBIC, fillcolor="white")


def _lighting_gradient(img: Image.Image, strength: float, rng: np.random.Generator):
    """Darken one side/corner, as a phone's own shadow or an off-centre lamp would."""
    if strength <= 0:
        return img
    w, h = img.size
    xs = np.linspace(0, 1, w)
    ys = np.linspace(0, 1, h)
    gx, gy = np.meshgrid(xs, ys)
    # random direction for the falloff
    ax, ay = rng.uniform(-1, 1), rng.uniform(-1, 1)
    field = ax * gx + ay * gy
    # np.ptp(field), not field.ptp() - the ndarray method was removed in numpy 2.0
    field = (field - field.min()) / max(1e-6, float(np.ptp(field)))  # 0..1
    mask = 1.0 - strength * field  # brightest at one end, dimmer at the other
    arr = np.asarray(img, dtype=np.float32)
    arr *= mask[:, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _jpeg_roundtrip(img: Image.Image, quality: int) -> Image.Image:
    import io

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def degrade(
    image: Image.Image,
    level: str = "moderate",
    seed: int | None = None,
) -> Image.Image:
    """Return a phone-photo-like version of a clean page image.

    Applied in the order a real capture introduces them: geometry first (the page is
    photographed at an angle), then lighting, then optics/blur, then sensor noise, then
    the JPEG the phone actually saves.
    """
    if level not in PROFILES:
        raise ValueError(f"unknown level {level!r}; expected one of {sorted(PROFILES)}")
    p = PROFILES[level]
    rng = np.random.default_rng(seed)
    img = image.convert("RGB")

    if p.perspective > 0:
        img = _perspective_warp(img, p.perspective, rng)
    if p.rotation_deg > 0:
        angle = rng.uniform(-p.rotation_deg, p.rotation_deg)
        img = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor="white")
    img = _lighting_gradient(img, p.lighting, rng)
    if p.contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(p.contrast)
    if p.blur_radius > 0:
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, p.blur_radius)))
    if p.noise_sigma > 0:
        arr = np.asarray(img, dtype=np.float32)
        arr += rng.normal(0, p.noise_sigma, arr.shape)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return _jpeg_roundtrip(img, p.jpeg_quality)
