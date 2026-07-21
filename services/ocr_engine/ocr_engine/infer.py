"""Full-page OCR: segment into lines, split each line into words, recognise, reassemble.

This is the inference entry point the API's ocr_client calls. Recognising word-sized crops
(rather than whole lines) keeps each image near-square, which is what TrOCR handles well.
It takes any Recognizer, so the same assembly is exercised in tests (StubRecognizer) and in
production (TrOCRRecognizer).
"""

from pathlib import Path

from PIL import Image

from ocr_engine.recognizer import Recognizer
from ocr_engine.segment import segment_lines, split_into_words


def extract_text_from_image(
    image_path: str | Path,
    recognizer: Recognizer,
    **segment_kwargs,
) -> str:
    """Return the recognised text of a report image, one line per detected text band."""
    image = Image.open(image_path)
    return extract_text_from_pil(image, recognizer, **segment_kwargs)


def extract_text_from_pil(image: Image.Image, recognizer: Recognizer, **segment_kwargs) -> str:
    lines = segment_lines(image, **segment_kwargs)
    if not lines:
        return ""

    # Flatten every word of every line into one batch, remembering which line each belongs
    # to, so the recogniser runs once and we can rebuild the lines afterwards.
    word_images: list[Image.Image] = []
    counts: list[int] = []
    for ln in lines:
        words = split_into_words(ln.image) or [ln.image]
        counts.append(len(words))
        word_images.extend(words)

    texts = recognizer.recognize_batch(word_images)

    out_lines: list[str] = []
    pos = 0
    for count in counts:
        line_words = [t.strip() for t in texts[pos : pos + count] if t.strip()]
        pos += count
        if line_words:
            out_lines.append(" ".join(line_words))
    return "\n".join(out_lines)
