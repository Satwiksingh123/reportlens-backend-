# data_synthesis

Generates **synthetic lab-report images with ground-truth labels** — the training data
for the custom OCR engine and an evaluation set for the parser.

Real lab reports can't be legally/ethically collected to train on, so we synthesize
unlimited labeled data instead. Because the generator reuses the **same reference table**
as [`medical_parser`](../medical_parser), the true status of every sampled value is known,
which lets us measure parser accuracy automatically (see the self-consistency test).

## What each sample contains

| File | Contents |
|---|---|
| `<id>.png` | rendered report image with realistic scan noise (skew, blur, speckle) |
| `<id>.gt.json` | ground truth: structured biomarkers (name/value/unit/range/**status**) + patient/lab metadata |
| `<id>.ocr.json` | OCR supervision: each text line and its bounding box |

## Usage

```bash
# generate 500 reports for OCR training
python -m data_synthesis.generate_dataset --count 500 --out data/synthetic/generated

# in code
from data_synthesis import generate_report, render_report
report = generate_report(panel="CBC", sex="M", seed=1)
img, boxes = render_report(report)
```

Value sampling is controllable via `abnormal_rate` so you can bias the dataset toward
abnormal cases, and every report is reproducible from a `seed`.

## Test

```bash
pytest -q          # 5 tests, incl. generator↔parser status agreement
ruff check .
```
