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

Testing the full OCR → medical_parser pipeline against these surfaced and fixed three real
parser bugs (see `services/medical_parser` git history around this date):
1. De-dup logic could keep a valueless "section heading" match (e.g. a bare "HEMOGLOBIN"
   heading) over the real data row appearing later.
2. "T3, TOTAL" / "T4, TOTAL" (reversed word order + comma) didn't match the "total t3" /
   "total t4" phrase aliases at all.
3. "Total Cholesterol/HDL Ratio" was matched as plain "Total Cholesterol" (a true substring
   match), and bare "Cholesterol" (without "Total") didn't match anything.

Known remaining gaps (not fixed, low impact / out of scope):
- One OCR reading-order edge case split a value onto an adjacent line for a single CBC row
  (MCH) in one report — a Tesseract layout quirk, not reproduced elsewhere.
- Thyroid Antibodies is not a supported v1 panel; the parser's short "tg" alias for
  Triglycerides false-matches "Anti-Tg" on that report. Not fixed since the panel itself is
  out of scope.
