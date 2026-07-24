# ocr_engine

A custom OCR pipeline for lab reports, in two halves:

```
page image ──▶ line segmentation (classical CV) ──▶ line crops ──▶ recogniser ──▶ text
                 no GPU, deterministic                              Tesseract (default)
```

- **Segmentation** (`segment.py`) — horizontal projection profiles find text bands and
  crop each line. Pure numpy/PIL, no training, runs anywhere.
- **Recognition** (`recognizer.py`):
  - `TesseractRecognizer` — **the default.** A mature, CPU-only OCR that is highly
    accurate on clean printed text like lab reports. No GPU, no training.
  - `TrOCRRecognizer` — an optional fine-tuned transformer path, kept as a from-scratch
    ML artifact (see the training notebook), not the default engine.
  - `StubRecognizer` — deterministic, for tests/offline.
- **Assembly** (`infer.py`) — `extract_text_from_image(path, recognizer)` segments a page
  into lines and recognises each; this is what the API calls.

## Run the demo (no GPU)

Open [`notebooks/ocr_demo_colab.ipynb`](notebooks/ocr_demo_colab.ipynb) in Colab and
*Run all* (about a minute) — it runs the Tesseract pipeline on synthetic reports and prints
the character accuracy. Or locally:

```bash
# needs the tesseract binary:  apt-get install tesseract-ocr   (macOS: brew install tesseract)
pip install -e "services/ocr_engine[ocr]"
python -m ocr_engine.sanity_check            # Tesseract, prints ground truth vs OCR + CER
```

## Optional: fine-tune a TrOCR recogniser (Colab GPU)

[`notebooks/train_ocr_colab.ipynb`](notebooks/train_ocr_colab.ipynb) is a self-contained
demonstration of a from-scratch fine-tuning pipeline: generate synthetic reports, crop
labelled column fields, fine-tune `microsoft/trocr-base-printed`, and evaluate with CER.
It is portfolio evidence of the ML workflow — the product itself runs on Tesseract.

```bash
python -m ocr_engine.sanity_check --engine trocr --model-dir artifacts/trocr-lab
```

## Develop (no GPU)

```bash
pip install -e ".[dev]"      # light: numpy + pillow only
ruff check .
pytest -q                     # segmentation + assembly (Tesseract test skips if not installed)
```
