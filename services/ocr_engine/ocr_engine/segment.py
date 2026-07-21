"""Classical line segmentation via horizontal projection profiles.

No training and no GPU: we binarise the page, sum ink per row to find text bands, then
crop each band to a line image for the recognizer. This is the "layout" half of the OCR
pipeline and runs anywhere. It is tuned for clean-ish lab-report scans (dark text on a
light background) which is exactly what the synthetic generator and real lab printouts
produce.
"""

from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass
class LineBox:
    box: tuple[int, int, int, int]  # (x0, y0, x1, y1)
    image: Image.Image


def _to_ink(gray: np.ndarray, ink_threshold: int) -> np.ndarray:
    """Boolean array: True where a pixel is dark enough to be ink."""
    return gray < ink_threshold


def segment_lines(
    image: Image.Image,
    ink_threshold: int = 160,
    min_ink_ratio: float = 0.01,
    min_line_height: int = 8,
    merge_gap: int = 4,
    pad: int = 4,
) -> list[LineBox]:
    """Split a page image into per-line crops, top to bottom.

    - ink_threshold: pixels darker than this count as ink.
    - min_ink_ratio: a row needs this fraction of its width in ink to be "text" (rejects
      speckle from scan noise).
    - merge_gap: text bands separated by <= this many blank rows are joined (keeps a line
      from splitting across descenders/thin gaps).
    - min_line_height: bands thinner than this are dropped.
    - pad: pixels of padding added around each crop.
    """
    gray = np.asarray(image.convert("L"))
    height, width = gray.shape
    ink = _to_ink(gray, ink_threshold)

    row_ink = ink.sum(axis=1)
    is_text_row = row_ink > (min_ink_ratio * width)

    bands = _rows_to_bands(is_text_row, merge_gap)

    lines: list[LineBox] = []
    for y0, y1 in bands:
        if (y1 - y0) < min_line_height:
            continue
        # Trim horizontal extent to the real text ink. A column must have ink over a
        # minimum share of the band height to count - a lone speckle dot (1-2px) does not.
        # Without this, scan speckle scattered across the page stretches every crop to full
        # width, and TrOCR's square resize then crushes the text into an unreadable smear.
        band_ink = ink[y0:y1]
        col_ink = band_ink.sum(axis=0)
        col_thresh = max(2, int(0.2 * (y1 - y0)))
        cols = np.where(col_ink >= col_thresh)[0]
        if cols.size == 0:
            continue
        x0, x1 = int(cols[0]), int(cols[-1]) + 1

        bx0 = max(0, x0 - pad)
        by0 = max(0, y0 - pad)
        bx1 = min(width, x1 + pad)
        by1 = min(height, y1 + pad)
        crop = image.crop((bx0, by0, bx1, by1))
        lines.append(LineBox(box=(bx0, by0, bx1, by1), image=crop))

    return lines


def split_into_words(
    line_image: Image.Image,
    ink_threshold: int = 160,
    min_gap: int | None = None,
    pad: int = 2,
) -> list[Image.Image]:
    """Split a single line crop into word images by gaps in the vertical ink profile.

    Blank-column runs wider than `min_gap` are treated as spaces between words. `min_gap`
    defaults to a fraction of the line height, since a space scales with the font size -
    this keeps within-word letter gaps from over-splitting while still separating words.
    Recognising word-sized crops (near-square) avoids the extreme horizontal squashing a
    whole line suffers when resized to TrOCR's 384x384 input.
    """
    gray = np.asarray(line_image.convert("L"))
    h, w = gray.shape
    if min_gap is None:
        # Only split clearly inter-column gaps. A single in-word space stays joined, which
        # is fine: those crops (e.g. "Bilirubin Total") are already short enough for TrOCR.
        min_gap = max(6, int(0.6 * h))
    ink_cols = (gray < ink_threshold).sum(axis=0) > 0

    words: list[Image.Image] = []
    start = None
    gap = 0
    for x in range(w):
        if ink_cols[x]:
            if start is None:
                start = x
            gap = 0
        else:
            if start is not None:
                gap += 1
                if gap >= min_gap:
                    end = x - gap + 1
                    words.append(_crop_word(line_image, start, end, pad, w, h))
                    start = None
    if start is not None:
        words.append(_crop_word(line_image, start, w, pad, w, h))
    return words


def _crop_word(img: Image.Image, x0: int, x1: int, pad: int, w: int, h: int) -> Image.Image:
    return img.crop((max(0, x0 - pad), 0, min(w, x1 + pad), h))


def _rows_to_bands(is_text_row: np.ndarray, merge_gap: int) -> list[tuple[int, int]]:
    """Convert a boolean per-row text mask into (start, end) bands, merging small gaps."""
    bands: list[tuple[int, int]] = []
    start = None
    for y, is_text in enumerate(is_text_row):
        if is_text and start is None:
            start = y
        elif not is_text and start is not None:
            bands.append((start, y))
            start = None
    if start is not None:
        bands.append((start, len(is_text_row)))

    if not bands:
        return []

    # merge bands separated by a gap <= merge_gap
    merged = [bands[0]]
    for s, e in bands[1:]:
        ps, pe = merged[-1]
        if s - pe <= merge_gap:
            merged[-1] = (ps, e)
        else:
            merged.append((s, e))
    return merged
