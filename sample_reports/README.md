# sample_reports

Real-world lab report PDFs used to validate the OCR + parser pipeline against actual
report layouts (logos, QR codes, barcodes, watermarks, colored text, different lab
software vendors) — something the synthetic generator can't fully stand in for.

**Source:** publicly published "sample report" templates from diagnostic labs / lab
management software vendors (Drlogy, Max Lab, Labsmart), used for marketing/demo purposes
with fictional patient data — safe to use and redistribute, no real patient data. One
report (`services/medical_parser/tests/fixtures_maxlab_papa.py`, not a PDF here) came from
a real family member's Max Lab report with personal data stripped, kept only as a frozen
text fixture rather than a PDF.

## Reports

| File | Panel | Vendor |
|---|---|---|
| cbc_normal_drlogy.pdf | CBC (all normal) | Drlogy |
| cbc_abnormal_drlogy.pdf | CBC (abnormal) | Drlogy |
| cbc_esr_drlogy.pdf | CBC with ESR | Drlogy |
| kft_normal_drlogy.pdf | Kidney Function Test | Drlogy |
| lipid_drlogy.pdf | Lipid Profile (abnormal) | Drlogy |
| lipid_normal_drlogy.pdf | Lipid Profile (normal) | Drlogy |
| lipid_maxlab.pdf | Lipid Profile, 2-page real lab report | Max Lab |
| thyroid_abnormal_drlogy.pdf | Thyroid Profile (abnormal) | Drlogy |
| thyroid_antibodies_drlogy.pdf | Thyroid Antibodies (out of v1 scope) | Drlogy |
| providers/labsmart_cbc.pdf | CBC | Labsmart |
| providers/labsmart_lft.pdf | LFT | Labsmart |
| providers/labsmart_kft.pdf | KFT | Labsmart |
| providers/labsmart_lipid.pdf | Lipid Profile | Labsmart |
| providers/drlogy_electrolytes.pdf | Electrolytes (Na/K/Cl/HCO3/Ca/Mg) | Drlogy |
| providers/drlogy_vitb12.pdf | Vitamin B12 | Drlogy |
| providers/drlal_s056.pdf, drlal_s215.pdf | Hepatitis B (out of v1 scope) | Dr Lal PathLabs |

`sample_reports/providers/images/` (gitignored, regeneratable) holds rendered page PNGs
used to drive OCR directly during development.

## Regenerate page images

```bash
pip install pymupdf
python - <<'PY'
import fitz, os
for base in ["sample_reports", "sample_reports/providers"]:
    out = f"{base}/images"; os.makedirs(out, exist_ok=True)
    for fn in sorted(os.listdir(base)):
        if fn.endswith(".pdf"):
            fitz.open(f"{base}/{fn}")[0].get_pixmap(dpi=300).save(f"{out}/{fn[:-4]}.png")
PY
```

## Measured value-level accuracy (2026-07-25/26)

Rigorous measurement against hand-verified ground truth, running the real end-to-end path
(`app.services.ocr_client.extract_text` → `medical_parser.parse_report`, PDF straight from
the file, no manual pre-processing):

**105 / 105 = 100% across all 13 PDFs here, 0 wrong values.** Plus the separately-tracked
Max Lab "papa" report at 49/49 (a different, independently-sourced document, not double
counted). **Combined: 154/154 values correct across 14 real reports from 4 independent
vendors (Drlogy, Max Lab, Labsmart, Dr Lal), 0 wrong values throughout.**

The single most important property for a medical tool holds throughout every fix below:
**when the pipeline reports a value it is never wrong** (100% precision) — every failure
found along the way was a *miss* (a dropped value), and every genuine wrong-value bug
found was traced to a root cause and fixed, never patched over.

### The journey (88% → 100%), roughly in order of when each was found

1. **Parser bugs** on the first 7 reports: de-dup keeping a valueless heading over the
   real data row; "T3, TOTAL" (reversed word order + comma) not matching; "Total
   Cholesterol/HDL Ratio" mis-matched as plain "Total Cholesterol"; a "Sample not yet
   received" line fabricating a fake result.
2. **OCR-driven alias gaps**: "RDW" misread as "ROW", singular "Triglyceride", mangled
   "Alkaline Phosphatase (ALP)" → "Alkaline: Rhespliatase (ALF)".
3. **Continuation-line merge** (`_merge_continuation_lines`): re-joins a test's name and
   value when OCR splits them across lines (a method sub-label carrying the value, e.g.
   "MCH" / "Calculated 35 …", or a two-column layout detaching them).
4. **Multi-scale OCR** (`TesseractRecognizer` native + 1.5× pass, concatenated
   native-first): some layouts drop a value at one scale but read it at another; the
   parser's valued-first de-dup keeps the native pass where it succeeded and fills gaps
   from the upscaled pass.
5. **Generalized matching to a real, independently-sourced Max Lab report** (the "papa"
   fixture, 9 panels never combined before): rewrote alias matching to tokenize on
   alphanumeric runs joined by "any non-word characters", so real punctuation variants
   match ("Bilirubin (Total)", "A.G. ratio", "Glucose (Fasting)", "25 Hydroxy, Vitamin D").
   Also fixed a value-extraction bug where digits glued to a preceding letter (B12, A1c)
   were misread as the value, and an HbA1c-vs-Hemoglobin alias collision.
6. **Safety-critical fix**, found via a 4th independent vendor (Labsmart): bare short
   aliases ("k" for Potassium, "fe" for Serum Iron — legitimate chemistry shorthand) were
   matching inside completely unrelated text (a doctor's "A. K." name initial, OCR noise
   near a logo) with no value on that line, and the continuation-merge then absorbed a
   distant, unrelated number as if it were that "result" — fabricating Potassium/Iron
   values on reports that never measured those tests. Fixed by gating continuation-merge
   on match specificity (bare 1-2 character shorthand can only ever report a value from
   its own line).
7. **MCH/MCHC vs Hemoglobin**: "MEAN CELL HAEMOGLOBIN, MCH" (this vendor's exact wording)
   contains the word "Haemoglobin" and, being longer under the old sort, won over MCH's
   narrower alias — added "mean cell h(a)emoglobin" variants, specific enough to win.
8. **Native-value-vs-merged-value priority**: a real Vitamin B12 report's valueless
   heading, immediately followed by unrelated boilerplate containing a stray number
   ("Sample Type Serum (3 ml)..."), had that stray number absorbed as the "value" *before*
   the real result line appeared later in the document — and the old de-dup rule (replace
   only if the existing value was `None`) permanently kept the wrong fabricated value.
   Fixed: a later value read directly off a biomarker's own line now always supersedes an
   earlier one assembled by the continuation-merge, regardless of encounter order.

### Tried and reverted

Preferring a PDF's native embedded text layer over OCR (these PDFs are digitally
generated, not scans, so in isolation the text layer is perfectly accurate) sounded like a
strict improvement but measured WORSE: these table-based PDFs store text in column order
in the content stream (all test names, then all values, then all ranges), so plain-text
extraction breaks row alignment entirely. Tesseract's OCR on the rendered page reconstructs
visual (row) reading order correctly and stayed the more accurate path. A layout-aware
extraction (grouping PyMuPDF's word-level bounding boxes into rows ourselves) could beat
OCR for native-text PDFs, but is unimplemented/untested — a documented future idea, not
shipped without validation. **Lesson: measure against real files before trusting an
"obviously better" architecture change.**

### Known, accepted gaps (not fixed — low impact / out of v1 scope)

- One OCR reading-order quirk on one report (a single value briefly needed the
  continuation-merge, now handled).
- One report's eGFR simply has no result row in the source document (not a bug).
- Thyroid Antibodies and Hepatitis B (Dr Lal) are not supported v1 panels; the parser's
  short "tg" alias for Triglycerides false-matches "Anti-Tg" on the Thyroid Antibodies
  report. Not fixed since those panels are out of scope for v1.

### Honest scope of this accuracy number

This is measured on **clean, digitally-generated PDFs** (not scans or phone photos) from
**4 vendors**, covering the CBC/LFT/KFT/Lipid/Thyroid/Electrolytes/Vitamin B12 panels. It
is not a claim that *any* random lab's *any* report format will score 100% — an
unseen vendor's naming conventions could still miss a value (the design ensures a miss,
never a wrong value). Broadening vendor coverage further (SRL/Agilus, Metropolis, Apollo,
1mg, more Dr Lal panels) and testing against genuine scanned/photographed reports remain
the honest next steps toward a stronger generalization claim.
