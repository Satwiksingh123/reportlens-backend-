# ocr_engine

A custom OCR pipeline for lab reports, in two halves:

```
page image ──▶ line segmentation (classical CV) ──▶ line crops ──▶ TrOCR recogniser ──▶ text
                 no GPU, deterministic                              fine-tuned on Colab
```

- **Segmentation** (`segment.py`) — horizontal projection profiles find text bands and
  crop each line. Pure numpy/PIL, no training, runs anywhere.
- **Recognition** (`recognizer.py`) — `TrOCRRecognizer` wraps a fine-tuned
  `microsoft/trocr-small-printed`. `StubRecognizer` stands in for tests/offline.
- **Assembly** (`infer.py`) — `extract_text_from_image(path, recognizer)` ties them
  together; this is what the API calls.
- **Training** (`train_trocr.py`, `dataset.py`) — generate synthetic reports, crop
  labelled lines, fine-tune TrOCR, report CER.

## Train the recogniser (Google Colab, free GPU)

You cannot train this on a laptop without an NVIDIA GPU — use the notebook.

1. Open [`notebooks/train_ocr_colab.ipynb`](notebooks/train_ocr_colab.ipynb) in Google
   Colab (upload it, or in Colab: *File → Open notebook → GitHub → paste the repo URL*).
2. *Runtime → Change runtime type → T4 GPU → Save.*
3. *Runtime → Run all.* That's it — the notebook clones the repo, installs deps,
   generates 800 synthetic reports, fine-tunes TrOCR (~15–30 min), prints the **CER**,
   and downloads `trocr-lab.zip`.

No coding required — just run the cells. Tune `--num-reports` / `--epochs` in the train
cell for a stronger model.

## Use the fine-tuned model locally (inference, CPU is fine)

```bash
pip install -e "services/ocr_engine[train]"   # torch + transformers for inference
# unzip the model you trained, e.g. to services/ocr_engine/artifacts/trocr-lab
```
```python
from ocr_engine.recognizer import TrOCRRecognizer
from ocr_engine.infer import extract_text_from_image

rec = TrOCRRecognizer(model_dir="artifacts/trocr-lab")
print(extract_text_from_image("some_report.png", rec))
```

The API's `ocr_client` loads this automatically when `OCR_MODEL_DIR` points at a trained
model; otherwise it falls back to a deterministic stub so the pipeline still runs.

## Develop (no GPU)

```bash
pip install -e ".[dev]"     # light: numpy + pillow only
ruff check .
pytest -q                    # segmentation + assembly, via StubRecognizer
```

> The synthetic fonts/layout are consistent, so CER on synthetic data goes very low —
> that is expected. The portfolio value is the end-to-end custom pipeline (synthetic data
> → segmentation → fine-tuned recognition), not the headline number.
