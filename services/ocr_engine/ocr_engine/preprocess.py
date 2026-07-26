"""Image preprocessing for photographed / scanned reports.

Clean PDF renders need none of this - they are already upright, evenly lit and noise-free.
A phone photo is not: it arrives rotated a few degrees, lit unevenly across the page, and
softened by blur and JPEG. Those three things are what OCR is most sensitive to, so this
module addresses exactly them and nothing more:

  deskew            - projection-profile search for the rotation that makes text rows
                      sharpest; a couple of degrees of skew measurably hurts line
                      segmentation and recognition.
  flatten_lighting  - divide out a large-scale background estimate, so a page that is
                      bright on one side and dim on the other becomes uniform. This is
                      what breaks a single global threshold on photos.

Every function is a no-op-safe transform: given an already-clean page it returns something
equivalent, so the same path can be used for both PDFs and photos.
"""

import numpy as np
from PIL import Image, ImageFilter


def _to_gray_array(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("L"), dtype=np.float32)


def estimate_skew(image: Image.Image, max_angle: float = 8.0, coarse_step: float = 1.0) -> float:
    """Estimate the page's rotation in degrees (positive = rotate this much to correct).

    Scores a candidate angle by the variance of the horizontal ink profile: when text rows
    are level, rows alternate sharply between "line" and "gap", maximising variance. A
    coarse sweep then a fine refinement keeps this cheap (a full 0.1-degree sweep over the
    whole page is needlessly slow for the same answer).
    """
    # work small - skew is a global property and downscaling makes the sweep much cheaper
    small = image.convert("L")
    small.thumbnail((900, 900))
    base = np.asarray(small, dtype=np.float32)
    ink = 255.0 - base  # ink high, paper low

    def sharpness(angle: float) -> float:
        if angle == 0.0:
            rotated = ink
        else:
            rotated = np.asarray(
                Image.fromarray(ink).rotate(angle, resample=Image.BILINEAR, fillcolor=0),
                dtype=np.float32,
            )
        profile = rotated.sum(axis=1)
        return float(np.var(profile))

    coarse = np.arange(-max_angle, max_angle + coarse_step, coarse_step)
    best = max(coarse, key=sharpness)
    fine = np.arange(best - coarse_step, best + coarse_step + 0.1, 0.1)
    return float(max(fine, key=sharpness))


def deskew(image: Image.Image, max_angle: float = 8.0) -> Image.Image:
    """Rotate the page so its text rows are level. Returns the input if already straight."""
    angle = estimate_skew(image, max_angle=max_angle)
    if abs(angle) < 0.1:
        return image
    return image.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor="white")


def flatten_lighting(image: Image.Image, blur_radius: int = 45) -> Image.Image:
    """Remove large-scale brightness variation (a lamp to one side, the phone's shadow).

    Estimates the background by heavily blurring the page - at that radius only the
    illumination survives, not the text - then divides it out. Text keeps its contrast
    while the paper becomes uniformly bright.
    """
    gray = image.convert("L")
    background = gray.filter(ImageFilter.GaussianBlur(blur_radius))
    g = np.asarray(gray, dtype=np.float32)
    b = np.asarray(background, dtype=np.float32)
    b = np.maximum(b, 1.0)  # never divide by zero
    flat = np.clip(g / b * 255.0, 0, 255)
    return Image.fromarray(flat.astype(np.uint8)).convert("RGB")


def prepare_photo(image: Image.Image) -> Image.Image:
    """Full preprocessing chain for a photographed/scanned page: flatten, then deskew.

    Lighting is flattened first: skew estimation reads the ink profile, which a strong
    brightness gradient distorts.
    """
    return deskew(flatten_lighting(image))
