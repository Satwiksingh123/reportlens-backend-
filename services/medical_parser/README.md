# medical_parser

Turns raw OCR text from a lab report into structured biomarkers:
`{panel, test_name, value, unit, reference_range, status}`.

## How it works

1. **Reference knowledge base** ([`reference_ranges.py`](medical_parser/reference_ranges.py)) —
   a curated table of biomarkers across all 13 v1 panels, each with canonical name,
   aliases (spellings/abbreviations seen on real reports), unit, and a sex-aware fallback
   reference interval.
2. **Line parser** ([`parser.py`](medical_parser/parser.py)) — for each text line:
   - boundary-aware alias matching (so `Na` matches sodium but not the word "Name"),
   - numeric value extracted *after* the matched name (so digits inside names like
     `T3`, `B12`, `25-OH`, `HbA1c` are never mistaken for the value),
   - reference range: the one **printed on the report wins**; otherwise the sex-aware
     fallback from the KB,
   - status classified Low / Normal / High, handling one-sided ranges (`<200`, `>40`).

The deterministic rules are the ground-truth-checked backbone; a learned NER layer is
planned on top to catch irregular layouts the rules miss.

> Reference intervals in the KB are **illustrative** and lab/method dependent. In
> production the range printed on the report is always preferred.

## Usage

```python
from medical_parser import parse_report

rows = parse_report("Hemoglobin 11.2 g/dL 13.0-17.0", sex="M")
# [ParsedBiomarker(panel='CBC', test_name='Hemoglobin', value='11.2',
#                  unit='g/dL', reference_range='13.0-17.0', status='Low')]
```

## Test

```bash
pytest -q          # 13 tests
ruff check .
```
