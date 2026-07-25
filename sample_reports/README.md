# sample_reports

Real-world lab report PDFs used to validate the OCR + parser pipeline against actual
report layouts (logos, QR codes, barcodes, watermarks, colored text) — something the
synthetic generator can't fully stand in for.

**Source:** publicly published "sample report" templates from diagnostic lab / lab-software
sites (Drlogy, Max Lab), used for marketing/demo purposes with fictional patient data. Safe
to use and redistribute — no real patient data.

| File | Panel | Source |
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

## Regenerate the page images used for testing

```bash
pip install pymupdf
python - <<'PY'
import fitz, os
os.makedirs("sample_reports/images", exist_ok=True)
for fn in sorted(os.listdir("sample_reports")):
    if fn.endswith(".pdf"):
        doc = fitz.open(f"sample_reports/{fn}")
        doc[0].get_pixmap(dpi=300).save(f"sample_reports/images/{fn[:-4]}.png")
PY
```

## Findings from testing against these (2026-07-25)

OCR (Tesseract, whole-page `--psm 6`) reads the actual result rows (test name / value /
unit / range) with very high fidelity across all 9 reports — the only unreliable regions
are decorative (logo header, QR code area, barcode/signature footer), which the parser
never reads anyway.

Testing the full **PDF upload → OCR → medical_parser** pipeline (the real end-to-end path,
via `app.services.ocr_client.extract_text`) against these surfaced and fixed four real bugs:
1. De-dup logic could keep a valueless "section heading" match (e.g. a bare "HEMOGLOBIN"
   heading) over the real data row appearing later.
2. "T3, TOTAL" / "T4, TOTAL" (reversed word order + comma) didn't match the "total t3" /
   "total t4" phrase aliases at all.
3. "Total Cholesterol/HDL Ratio" was matched as plain "Total Cholesterol" (a true substring
   match), and bare "Cholesterol" (without "Total") didn't match anything.
4. A line noting a test wasn't actually run (e.g. "... Sample not yet received") could still
   have a nearby stray number fabricated into a fake result with a fake Low/High status.
   Lines containing "not yet received", "sample rejected", "results awaited", etc. are now
   skipped entirely.

PDF upload support was also added (`ocr_engine.pdf_utils.pdf_to_images` + `pymupdf`) since
real reports are usually uploaded as PDFs, not raw images — previously only image content
types reached the recogniser.

**Tried and reverted:** preferring the PDF's native embedded text layer over OCR (these
PDFs are digitally generated, not scans, so the text layer is perfectly accurate in
isolation) sounded like a strict improvement but measured WORSE - these table-based PDFs
store text in column order in the content stream (all test names, then all values, then
all ranges), so PyMuPDF's plain-text extraction breaks row alignment between a test's
name/value/range entirely. Tesseract's OCR on the rendered page reconstructs visual (row)
reading order correctly and stayed the more accurate path. A layout-aware extraction
(grouping PyMuPDF's word-level bounding boxes into rows ourselves) could beat OCR for
native-text PDFs, but is unimplemented/untested - a documented future idea, not shipped
without validation. Lesson: measure against the real files before trusting an "obviously
better" architecture change.

**Current state (2026-07-25):** across all 9 real PDFs, straight from the file (no manual
pre-processing), the full pipeline extracts 71 biomarker rows with only 3 missing values,
all documented, known, low-priority edge cases:
- One OCR reading-order quirk splits a value onto an adjacent line for a single CBC row
  (MCH) in one report — a Tesseract layout artifact, not reproduced elsewhere.
- One report's eGFR simply has no result row in the source document (not a bug).
- Thyroid Antibodies is not a supported v1 panel; the parser's short "tg" alias for
  Triglycerides false-matches "Anti-Tg" there. Not fixed since the panel itself is out of
  scope for v1.
