"""Line recognizers: turn a single cropped line image into text.

`Recognizer` is the interface the inference pipeline depends on. Two implementations:
  - StubRecognizer: deterministic, dependency-free, for tests and offline assembly checks.
  - TrOCRRecognizer: the fine-tuned model (optional `train` extra; lazy imports torch).
"""

from pathlib import Path
from typing import Protocol

from PIL import Image


class Recognizer(Protocol):
    def recognize(self, image: Image.Image) -> str:
        ...

    def recognize_batch(self, images: list[Image.Image]) -> list[str]:
        ...


class StubRecognizer:
    """Returns a fixed token per line. Lets us test segmentation + assembly without a model."""

    def __init__(self, token: str = "LINE"):
        self._token = token

    def recognize(self, image: Image.Image) -> str:
        return self._token

    def recognize_batch(self, images: list[Image.Image]) -> list[str]:
        return [self._token for _ in images]


class TrOCRRecognizer:  # pragma: no cover - requires the optional train extra + weights
    """Fine-tuned (or base) TrOCR recognition. Loads lazily so importing ocr_engine stays
    cheap and the API can fall back when torch/weights are absent."""

    def __init__(self, model_dir: str = "microsoft/trocr-base-printed", device: str | None = None):
        # Checked before importing torch: a path-like model_dir that doesn't exist would
        # otherwise be treated as a Hub repo id and fail with a confusing HTTP 401/404.
        if ("/" in model_dir or "\\" in model_dir) and not Path(model_dir).exists():
            raise FileNotFoundError(
                f"OCR model directory not found: {model_dir!r}. Train it first "
                "(services/ocr_engine/notebooks/train_ocr_colab.ipynb) or pass a Hugging "
                "Face model id such as 'microsoft/trocr-small-printed'."
            )

        import torch
        from transformers import VisionEncoderDecoderModel

        from ocr_engine.train_trocr import load_processor

        self._torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = load_processor(model_dir)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_dir).to(self.device)
        self.model.eval()

    def recognize(self, image: Image.Image) -> str:
        return self.recognize_batch([image])[0]

    def recognize_batch(self, images: list[Image.Image]) -> list[str]:
        if not images:
            return []
        from ocr_engine.preprocess import letterbox_square

        # Measured directly against ground truth: crops are correctly and completely
        # bounded (sometimes with margin to spare), yet generation still stops early
        # ("mg/dL" -> "mg/") - the model commits to EOS before the visible content is
        # exhausted. min_new_tokens, estimated from each crop's own width/height (before
        # letterboxing), forces the decoder past that point instead of tuning search
        # ranking (length_penalty alone did not change output at all - proof the correct
        # continuation wasn't even in the beam). Generated one crop at a time since
        # min_new_tokens is a single scalar per generate() call, not per-batch-item.
        results = []
        for raw in images:
            min_new = _estimate_min_new_tokens(raw)
            pixel_values = self.processor(
                images=letterbox_square(raw), return_tensors="pt"
            ).pixel_values.to(self.device)
            with self._torch.no_grad():
                generated = self.model.generate(
                    pixel_values,
                    max_new_tokens=32,
                    min_new_tokens=min_new,
                    num_beams=4,
                    no_repeat_ngram_size=3,
                    length_penalty=1.4,
                    early_stopping=False,
                )
            text = self.processor.batch_decode(generated, skip_special_tokens=True)[0]
            results.append(text.strip())
        return results


def _estimate_min_new_tokens(
    image: Image.Image, char_aspect: float = 0.32, tokens_per_char: float = 0.6
) -> int:
    """Estimate a conservative minimum token count from a crop's raw width/height.

    `char_aspect` ~ typical character width/height for this font (measured locally from
    synthetic crops: ~0.26-0.32). `tokens_per_char` < 1 because BPE tokens often span more
    than one character, so this deliberately underestimates rather than forcing garbage
    past a genuinely short word.
    """
    w, h = image.size
    if h == 0:
        return 1
    num_chars = w / (h * char_aspect)
    return max(1, min(20, round(num_chars * tokens_per_char)))
