"""Real Labsmart (a third, independent lab-software vendor - different template engine
from Drlogy/Max Lab) sample report PDFs, condensed from the actual captured OCR output
(PDF -> pdf_to_images -> TesseractRecognizer.read_page, native + 1.5x multi-scale, exactly
as production runs it): the exact result-line wording is preserved verbatim, but the
duplicate multi-scale pass and non-result boilerplate/noise lines are trimmed for a
readable fixture. Paired with hand-verified ground truth.

Source: labsmartlis.com publicly published sample-report PDFs (placeholder patient data,
safe to use). See sample_reports/README.md for the source URLs and sample_reports/providers/
for the original PDFs this was captured from.

Kept as plain text (not re-running OCR in every test) so this suite is fast and
independent of whether tesseract is installed in CI, while still exercising the exact
real-world phrasing that broke the parser when this fixture was captured.
"""

LABSMART_CBC_TEXT = """
Regd. No.: XXXX54826XX
Labsmart Software
Mr. Saubhik Bhaumik
Age/Sex :27YRS/M Registered on : 17/10/2024 04:55 PM
Referred by : Self Collected on : 17/10/2024
Reg. no : 1001 Received on : 17/10/2024
Reported on : 17/10/2024 04:55 PM
HAEMATOLOGY
COMPLETE BLOOD COUNT (CBC)
TEST VALUE UNIT REFERENCE
HEMOGLOBIN 15 g/dl 13-17
TOTAL LEUKOCYTE COUNT 5,100 cumm 4,800 - 10,800
DIFFERENTIAL LEUCOCYTE COUNT
NEUTROPHILS 79 % 40 - 80
LYMPHOCYTE L 18 % 20 - 40
EOSINOPHILS 1 % 1-6
MONOCYTES L 1 % 2-10
BASOPHILS 1 % <2
PLATELET COUNT 3.5 lakhs/cumm 1.5-4.1
TOTAL RBC COUNT 5 million/cumm 4.5-5.5
HEMATOCRIT VALUE, HCT 42 % 40 - 50
MEAN CORPUSCULAR VOLUME, MCV 84.0 fL 83 - 101
MEAN CELL HAEMOGLOBIN, MCH 30.0 Pg 27 - 32
MEAN CELL HAEMOGLOBIN CON, MCHC H 35.7 % 31.5 - 34.5
Mr. Sachin Sharma Dr. A. K. Asthana
DMLT, Lab Incharge Page 1 of 2 MBBS, MD Pathologist
"""

LABSMART_CBC_GT = {
    "Hemoglobin": "15",
    "WBC Count": "5100",
    "Neutrophils": "79",
    "Lymphocytes": "18",
    "Eosinophils": "1",
    "Monocytes": "1",
    "Basophils": "1",
    "Platelet Count": "3.5",
    "RBC Count": "5",
    "Hematocrit": "42",
    "MCV": "84.0",
    "MCH": "30.0",
    "MCHC": "35.7",
}

LABSMART_LFT_TEXT = """
BIOCHEMISTRY
LIVER FUNCTION TEST (LFT)
TEST VALUE UNIT REFERENCE
SERUM BILIRUBIN (TOTAL) 0.9 mg/dl 0.2 - 1.2
SERUM BILIRUBIN (DIRECT) 0.2 mg/dl 0 - 0.3
SERUM BILIRUBIN (INDIRECT) 0.70 mg/dl 0.2 - 1
SGPT (ALT) 36 U/I 13 - 40
SGOT (AST) 32 U/I 0 - 37
SERUM ALKALINE PHOSPHATASE 11 U/I
SERUM PROTEIN 7.2 g/dl 6.4 - 8.3
SERUM ALBUMIN 4.7 g/dl 3.5 - 5.2
GLOBULIN 2.50 g/dl 1.8 - 3.6
A/G RATIO 1.88 1.1 - 2.1
"""

LABSMART_LFT_GT = {
    "Bilirubin Total": "0.9",
    "Bilirubin Direct": "0.2",
    "Bilirubin Indirect": "0.70",
    "SGPT (ALT)": "36",
    "SGOT (AST)": "32",
    "Alkaline Phosphatase": "11",
    "Total Protein": "7.2",
    "Albumin": "4.7",
    "Globulin": "2.50",
    "A/G Ratio": "1.88",
}

LABSMART_KFT_TEXT = """
BIOCHEMISTRY
KIDNEY FUNCTION TEST (KFT)
TEST VALUE UNIT REFERENCE
BUN 15.88 mg/dl 7.9 - 20
SERUM UREA 34 mg/dl 19 - 45
SERUM CREATININE 1.17 mg/dl 0.72 - 1.18
EGFR
Method: Calculated
L 87.08 ml/min/1.73m^2 > 90
EGFR CATEGORY
Method: Calculated
G2
SERUM CALCIUM 10 mg/dl 8.8 - 10.6
SERUM POTASSIUM 4 mmol/L 3.5 - 5.1
SERUM SODIUM 142 mmol/L 136 - 146
SERUM URIC ACID 7.1 mg/dl 3.5 - 7.2
UREA / CREATININE RATIO 29.06
BUN / CREATININE RATIO 13.57
"""

LABSMART_KFT_GT = {
    "BUN": "15.88",
    "Urea": "34",
    "Creatinine": "1.17",
    "eGFR": "87.08",
    "Calcium": "10",
    "Potassium": "4",
    "Sodium": "142",
    "Uric Acid": "7.1",
}

LABSMART_LIPID_TEXT = """
BIOCHEMISTRY
LIPID PROFILE
TEST VALUE UNIT REFERENCE
TOTAL CHOLESTEROL 180 mg/dl 125 - 200
TRIGLYCERIDES 172 mg/dl 25 - 200
HDL CHOLESTEROL 55 mg/dl 35 - 80
LDL CHOLESTEROL 90.60 mg/dl 85 - 130
VLDL CHOLESTEROL 34.40 mg/dl 5 - 40
LDL / HDL 1.65 1.5 - 3.5
TOTAL CHOLESTEROL / HDL L 3.27 3.5 - 5
TG / HDL 3.13
NON-HDL CHOLESTEROL 125.00
"""

LABSMART_LIPID_GT = {
    "Total Cholesterol": "180",
    "Triglycerides": "172",
    "HDL Cholesterol": "55",
    "LDL Cholesterol": "90.60",
    "VLDL Cholesterol": "34.40",
    "Cholesterol/HDL Ratio": "3.27",
    "Non-HDL Cholesterol": "125.00",
}

LABSMART_REPORTS = {
    "labsmart_cbc": (LABSMART_CBC_TEXT, LABSMART_CBC_GT),
    "labsmart_lft": (LABSMART_LFT_TEXT, LABSMART_LFT_GT),
    "labsmart_kft": (LABSMART_KFT_TEXT, LABSMART_KFT_GT),
    "labsmart_lipid": (LABSMART_LIPID_TEXT, LABSMART_LIPID_GT),
}
