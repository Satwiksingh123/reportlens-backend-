"""Line recognizers: turn a single cropped line image into text.

`Recognizer` is the interface the inference pipeline depends on. Two implementations:
  - StubRecognizer: deterministic, dependency-free, for tests and offline assembly checks.
  - TrOCRRecognizer: the fine-tuned model (optional `train` extra; lazy imports torch).
"""

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

    def __init__(self, model_dir: str = "microsoft/trocr-small-printed", device: str | None = None):
        import torch
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        self._torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = TrOCRProcessor.from_pretrained(model_dir)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_dir).to(self.device)
        self.model.eval()

    def recognize(self, image: Image.Image) -> str:
        return self.recognize_batch([image])[0]

    def recognize_batch(self, images: list[Image.Image]) -> list[str]:
        if not images:
            return []
        rgb = [im.convert("RGB") for im in images]
        pixel_values = self.processor(images=rgb, return_tensors="pt").pixel_values.to(self.device)
        with self._torch.no_grad():
            generated = self.model.generate(pixel_values, max_new_tokens=64)
        return [t.strip() for t in self.processor.batch_decode(generated, skip_special_tokens=True)]
