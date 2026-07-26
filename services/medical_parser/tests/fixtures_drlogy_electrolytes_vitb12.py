"""Two more real Drlogy sample reports, condensed from actual captured OCR output, filling
panel coverage gaps (a dedicated Electrolytes panel with all 6 biomarkers, and a
Vitamin B12-only report that also exercises the native-vs-merged-value bug: a valueless
"VITAMIN B12 (CYANOCOBALAMIN)" heading, followed by unrelated boilerplate containing a
stray number, followed by the real result line).
"""

DRLOGY_ELECTROLYTES_TEXT = """
ELECTROLYTES
Sodium 140.00 Normal 136.00 - 145.00 mEq/L
Potassium 4.50 Normal 3.50 - 5.10 mEq/L
Chloride 105.00 Normal 98.00 - 107.00 mEq/L
Bicarbonate 25.00 Normal 22.00 - 28.00 mEq/L
Calcium 9.00 Normal 8.60 - 10.20 mg/dL
Magnesium 2.00 Normal 1.80 - 2.30 mg/dL
"""

DRLOGY_ELECTROLYTES_GT = {
    "Sodium": "140.00",
    "Potassium": "4.50",
    "Chloride": "105.00",
    "Bicarbonate": "25.00",
    "Calcium": "9.00",
    "Magnesium": "2.00",
}

DRLOGY_VITB12_TEXT = """
VITAMIN B12 (CYANOCOBALAMIN)
Sample Type Serum (3 ml) TAT: 2hrs (Normal: 1 - 3 hrs)
VITAMIN B12 (CYANOCOBALAMIN) 452.00 Normal 200.00 - 900.00 pg/mL
"""

DRLOGY_VITB12_GT = {
    "Vitamin B12": "452.00",
}

DRLOGY_EXTRA_REPORTS = {
    "drlogy_electrolytes": (DRLOGY_ELECTROLYTES_TEXT, DRLOGY_ELECTROLYTES_GT),
    "drlogy_vitb12": (DRLOGY_VITB12_TEXT, DRLOGY_VITB12_GT),
}
