"""Real Max Lab 11-page full-body report reconstructed as OCR-style text (one line per
table row, method sub-labels on their own lines, exactly as Tesseract reads this lab's
layout - verified against the same lab's lipid_maxlab.pdf which OCRs cleanly).

Personal data removed - only the test table is kept. Used to harden the parser against a
real lab's naming conventions ("Bilirubin (Total)", "A.G. ratio", "Glucose (Fasting)",
"25 Hydroxy, Vitamin D", British "Leucocyte" spelling, etc.).
"""

# OCR-style page text (name value unit range on one line; method words on separate lines)
MAXLAB_PAPA_TEXT = """
CBC (Complete Blood Count), Whole Blood EDTA
Haemoglobin 15.3 g/dl 13.0 - 17.0
Packed Cell Volume (PCV) 45.5 % 40-50
Calculated
Total Leucocyte Count (TLC) 6.3 10~9/L 4.0-10.0
Electrical Impedance
RBC Count 5.0 10~12/L 4.5-5.5
MCV 90.2 fL 83-101
MCH 30.3 pg 27-32
MCHC 33.6 g/dl 31.5-34.5
Platelet Count 261.5 10~9/L 150-410
MPV 8.3 fl 7.8-11.2
RDW 13.4 % 11.5-14.5
Differential Cell Count
Neutrophils 44 % 40-80
Lymphocytes 46 % 20-40
Monocytes 08 % 2-10
Eosinophils 02 % 1-6
Basophils 00 % 0-2
Absolute Neutrophil Count 2.77 10~9/L 2.0-7.0
Absolute Lymphocyte Count 2.9 10~9/L 1.0-3.0
Absolute Monocyte Count 0.5 10~9/L 0.2-1.0
Absolute Eosinophil Count 0.13 10~9/L 0.02-0.5

Liver Function Test (LFT), Serum
Total Protein 7.05 g/dl 6.5 - 8.1
Albumin 4.6 g/dl 3.5 - 5.0
Globulin 2.4 g/dl 2.3 - 3.5
A.G. ratio 1.9 1.2 - 1.5
Bilirubin (Total) 1.58 mg/dl 0.3 - 1.2
Bilirubin (Direct) 0.52 mg/dl 0.1 - 0.5
Bilirubin (Indirect) 1.06 mg/dL 0.1 - 1.0
SGOT- Aspartate Transaminase (AST) 25.6 U/L < 50
SGPT- Alanine Transaminase (ALT) 34.1 U/L 17 - 63
AST/ALT Ratio 0.75 Ratio
Alkaline Phosphatase 63 U/L 32 - 91
GGTP (Gamma GT), Serum 30.9 U/L 7 - 50

Lipid Profile, Serum
Cholesterol 236 mg/dl < 200
HDL Cholesterol 37.0 mg/dl > 40
LDL Cholesterol 142 mg/dl < 100
Triglyceride 287.5 mg/dl < 150
VLDL Cholesterol 57.5 mg/dl < 30
Total Cholesterol/HDL Ratio 6.4 0.0-4.9
Non-HDL Cholesterol 199.00 mg/dL < 130
HDL/LDL 0.26 Ratio 0.3 - 0.4

Kidney Function Test (KFT) Profile
Urea 32.5 mg/dL 17.12 - 55.64
Blood Urea Nitrogen 15.19 mg/dl 8 - 26
Creatinine 1.01 mg/dl 0.61 - 1.24
eGFR by MDRD 78.19 ml/min/1.73 m2
eGFR by CKD EPI 2021 89.96
Bun/Creatinine Ratio 15.04 Ratio 12:1 - 20:1
Uric Acid 6.5 mg/dl 3.5 - 7.2
Calcium (Total) 10.2 mg/dl 8.9 - 10.3
Sodium 143.0 mmol/L 136 - 144
Potassium 4.8 mmol/L 3.6 - 5.1
Chloride 105 mmol/l 101-111

Vitamin B12 (Vit- B12) (Cyanocobalamin)
Vitamin B12 65 pg/mL 222 - 1439
Vitamin D 25 - Hydroxy Test (Vit. D3)
25 Hydroxy, Vitamin D 6.7 ng/mL 30-100

Fasting Blood Sugar (Glucose), (FBS), Fluoride Plasma
Glucose (Fasting) 94.3 mg/dl 74 - 99
HbA1c (Glycated/ Glycosylated Hemoglobin) Test, EDTA
Glycosylated Haemoglobin(Hb A1c) 5.60 % < 5.7
Average Glucose Value For the Last 3 Months 114.02 mg/dL

Iron, Serum
Iron 69.5 ug/dL 45 - 182

Total-Thyroid Profile (T3T4 & TSH)
T3 (Total) 1.0 ng/mL 0.87-1.78
T4 (Total) 7.3 ug/dL 5.93 - 13.29
TSH 1.2 uIU/ml 0.34-5.6
"""

# Ground truth: canonical test name -> value, for the 49 IN-SCOPE biomarkers only.
# (MPV, Absolute counts, AST/ALT Ratio, HDL/LDL, Bun/Creatinine Ratio, eGFR CKD-EPI dup,
#  Average Glucose are intentionally excluded - out of our 13-panel scope.)
MAXLAB_PAPA_GT = {
    "Hemoglobin": "15.3",
    "Hematocrit": "45.5",
    "WBC Count": "6.3",
    "RBC Count": "5.0",
    "MCV": "90.2",
    "MCH": "30.3",
    "MCHC": "33.6",
    "Platelet Count": "261.5",
    "RDW": "13.4",
    "Neutrophils": "44",
    "Lymphocytes": "46",
    "Monocytes": "8",
    "Eosinophils": "2",
    "Basophils": "0",
    "Total Protein": "7.05",
    "Albumin": "4.6",
    "Globulin": "2.4",
    "A/G Ratio": "1.9",
    "Bilirubin Total": "1.58",
    "Bilirubin Direct": "0.52",
    "Bilirubin Indirect": "1.06",
    "SGOT (AST)": "25.6",
    "SGPT (ALT)": "34.1",
    "Alkaline Phosphatase": "63",
    "GGT": "30.9",
    "Total Cholesterol": "236",
    "HDL Cholesterol": "37.0",
    "LDL Cholesterol": "142",
    "Triglycerides": "287.5",
    "VLDL Cholesterol": "57.5",
    "Cholesterol/HDL Ratio": "6.4",
    "Non-HDL Cholesterol": "199.00",
    "Urea": "32.5",
    "BUN": "15.19",
    "Creatinine": "1.01",
    "eGFR": "78.19",
    "Uric Acid": "6.5",
    "Calcium": "10.2",
    "Sodium": "143.0",
    "Potassium": "4.8",
    "Chloride": "105",
    "Vitamin B12": "65",
    "Vitamin D (25-OH)": "6.7",
    "Fasting Blood Sugar": "94.3",
    "HbA1c": "5.60",
    "Serum Iron": "69.5",
    "T3 Total": "1.0",
    "T4 Total": "7.3",
    "TSH": "1.2",
}
