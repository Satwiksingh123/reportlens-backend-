"""Line recognizers: turn a single cropped line image into text.

`Recognizer` is the interface the inference pipeline depends on. Implementations:
  - StubRecognizer: deterministic, dependency-free, for tests and offline assembly checks.
  - TesseractRecognizer: the default production engine - a mature, CPU-only OCR that is
    highly accurate on clean printed text like lab reports (no GPU, no training).
  - TrOCRRecognizer: the optional fine-tuned transformer path (see the Colab notebook);
    kept as a from-scratch ML artifact rather than the default engine.
"""

from pathlib import Path
from typing import Protocol

from PIL import Image


class Recognizer(Protocol):
    def recognize(self, image: Image.Image) -> str:
        ...

    def recognize_batch(self, images: list[Image.Image]) -> list[str]:
        ...


class TesseractRecognizer:
    """Tesseract OCR via pytesseract. Default production recogniser.

    Reads the whole page at once with Tesseract's own layout analysis (`--psm 4`, "single
    column of variable-size text"), the mode that scored best across environments: ~99%
    character accuracy locally and ~86% on Colab (the gap is font rendering - Windows
    Consolas vs Linux DejaVu). Far better than feeding it pre-cut line crops. `read_page`
    is the production entry point; per-line `recognize_batch` (`--psm 7`) is kept so the
    same class also fits the line-crop Recognizer protocol.

    Needs the `tesseract` binary (pre-installed on Colab; `apt-get install tesseract-ocr`
    on Debian/Ubuntu, or the UB-Mannheim installer on Windows) and the `ocr` extra. Honours
    the TESSERACT_CMD env var and falls back to the default Windows install path.
    """

    def __init__(self, lang: str = "eng", page_psm: int = 4, line_psm: int = 7):
        import os

        import pytesseract  # lazy: keeps ocr_engine importable without the ocr extra

        cmd = os.environ.get("TESSERACT_CMD")
        if not cmd and os.name == "nt":
            win = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            if os.path.exists(win):
                cmd = win
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd

        # Probe the binary now so a missing install fails at construction (letting callers
        # fall back) rather than deep inside the pipeline.
        pytesseract.get_tesseract_version()

        self._pt = pytesseract
        self.lang = lang
        self._page_config = f"--psm {page_psm}"
        self._line_config = f"--psm {line_psm}"

    def read_page(self, image: Image.Image) -> str:
        """Recognise a whole report image at once (the accurate production path)."""
        return self._pt.image_to_string(
            image.convert("RGB"), lang=self.lang, config=self._page_config
        ).strip()

    def recognize(self, image: Image.Image) -> str:
        return self.recognize_batch([image])[0]

    def recognize_batch(self, images: list[Image.Image]) -> list[str]:
        out = []
        for im in images:
            text = self._pt.image_to_string(
                im.convert("RGB"), lang=self.lang, config=self._line_config
            )
            out.append(text.strip())
        return out


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
        # Feed crops straight to the processor (plain resize to 384x384), matching TrOCR's
        # pretraining: word crops are aspect ~1-6, milder than the receipt lines TrOCR was
        # trained on, and this fills the frame with large glyphs. (An earlier letterbox
        # shrank wide words to tiny centred text; an earlier min_new_tokens floor made the
        # model invent trailing garbage - both removed.)
        rgb = [im.convert("RGB") for im in images]
        pixel_values = self.processor(images=rgb, return_tensors="pt").pixel_values.to(self.device)
        with self._torch.no_grad():
            generated = self.model.generate(
                pixel_values,
                max_new_tokens=32,
                num_beams=4,
                # length_penalty=1.0 (neutral) + early_stopping is the fix for garbage tails
                # ("0.3" -> "0.333533833G"): a model trained with length_penalty=1.4 baked
                # into its generation_config was rewarded for longer output and appended
                # junk after the real text. Passing these explicitly overrides the baked
                # config, so an already-trained model is fixed without retraining.
                length_penalty=1.0,
                early_stopping=True,
                no_repeat_ngram_size=3,  # guards against exact-loop repetition
            )
        return [t.strip() for t in self.processor.batch_decode(generated, skip_special_tokens=True)]
