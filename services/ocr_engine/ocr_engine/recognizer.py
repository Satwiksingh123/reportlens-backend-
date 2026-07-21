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

        rgb = [letterbox_square(im) for im in images]
        pixel_values = self.processor(images=rgb, return_tensors="pt").pixel_values.to(self.device)
        with self._torch.no_grad():
            generated = self.model.generate(
                pixel_values, max_new_tokens=32, num_beams=4, no_repeat_ngram_size=3
            )
        return [t.strip() for t in self.processor.batch_decode(generated, skip_special_tokens=True)]
