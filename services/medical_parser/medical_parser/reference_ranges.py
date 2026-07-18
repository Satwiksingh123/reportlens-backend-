"""Canonical biomarker reference data for the v1 lab panels.

IMPORTANT: these ranges are ILLUSTRATIVE adult reference intervals for building and
testing the parser. Real reference ranges depend on the testing lab, assay method,
age, sex, and physiological state (e.g. pregnancy). In production the parser prefers
the reference range *printed on the report itself*; this table is only the fallback
used for status classification when the report omits a range.

Each biomarker declares:
  - panel:    which report panel it belongs to
  - canonical: the normalized display name
  - aliases:  alternative spellings/abbreviations seen on real reports / OCR output
  - unit:     canonical unit
  - low/high: fallback reference interval (None where a simple numeric interval
              does not apply, e.g. qualitative urine findings)
  - sex:      "M", "F", or None (applies to any)
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BiomarkerRef:
    panel: str
    canonical: str
    unit: str | None
    low: float | None
    high: float | None
    aliases: tuple[str, ...] = field(default_factory=tuple)
    sex: str | None = None


# fmt: off
REFERENCE_TABLE: list[BiomarkerRef] = [
    # ---------- Complete Blood Count (CBC) ----------
    BiomarkerRef("CBC", "Hemoglobin", "g/dL", 13.0, 17.0, ("hb", "hgb", "haemoglobin"), "M"),
    BiomarkerRef("CBC", "Hemoglobin", "g/dL", 12.0, 15.0, ("hb", "hgb", "haemoglobin"), "F"),
    BiomarkerRef("CBC", "RBC Count", "million/uL", 4.5, 5.9, ("rbc", "red blood cell", "total rbc")),
    BiomarkerRef("CBC", "WBC Count", "/uL", 4000, 11000, ("wbc", "tlc", "total leukocyte", "white blood cell")),
    BiomarkerRef("CBC", "Platelet Count", "/uL", 150000, 410000, ("platelets", "plt")),
    BiomarkerRef("CBC", "Hematocrit", "%", 40.0, 50.0, ("hct", "pcv", "packed cell volume"), "M"),
    BiomarkerRef("CBC", "Hematocrit", "%", 36.0, 46.0, ("hct", "pcv", "packed cell volume"), "F"),
    BiomarkerRef("CBC", "MCV", "fL", 83.0, 101.0, ("mean corpuscular volume",)),
    BiomarkerRef("CBC", "MCH", "pg", 27.0, 32.0, ("mean corpuscular hemoglobin",)),
    BiomarkerRef("CBC", "MCHC", "g/dL", 31.5, 34.5, ("mean corpuscular hemoglobin concentration",)),
    BiomarkerRef("CBC", "RDW", "%", 11.6, 14.0, ("red cell distribution width",)),
    BiomarkerRef("CBC", "Neutrophils", "%", 40.0, 80.0, ("neutrophil",)),
    BiomarkerRef("CBC", "Lymphocytes", "%", 20.0, 40.0, ("lymphocyte",)),
    BiomarkerRef("CBC", "Monocytes", "%", 2.0, 10.0, ("monocyte",)),
    BiomarkerRef("CBC", "Eosinophils", "%", 1.0, 6.0, ("eosinophil",)),
    BiomarkerRef("CBC", "Basophils", "%", 0.0, 2.0, ("basophil",)),

    # ---------- Liver Function Test (LFT) ----------
    BiomarkerRef("LFT", "Bilirubin Total", "mg/dL", 0.3, 1.2, ("total bilirubin", "t.bilirubin", "s.bilirubin total")),
    BiomarkerRef("LFT", "Bilirubin Direct", "mg/dL", 0.0, 0.3, ("direct bilirubin", "conjugated bilirubin")),
    BiomarkerRef("LFT", "Bilirubin Indirect", "mg/dL", 0.1, 1.0, ("indirect bilirubin", "unconjugated bilirubin")),
    BiomarkerRef("LFT", "SGPT (ALT)", "U/L", 7.0, 56.0, ("alt", "sgpt", "alanine aminotransferase")),
    BiomarkerRef("LFT", "SGOT (AST)", "U/L", 5.0, 40.0, ("ast", "sgot", "aspartate aminotransferase")),
    BiomarkerRef("LFT", "Alkaline Phosphatase", "U/L", 44.0, 147.0, ("alp", "alk phos")),
    BiomarkerRef("LFT", "Total Protein", "g/dL", 6.0, 8.3, ("protein total",)),
    BiomarkerRef("LFT", "Albumin", "g/dL", 3.5, 5.2, ("alb",)),
    BiomarkerRef("LFT", "Globulin", "g/dL", 2.0, 3.5, ()),
    BiomarkerRef("LFT", "A/G Ratio", None, 1.0, 2.1, ("albumin globulin ratio",)),
    BiomarkerRef("LFT", "GGT", "U/L", 8.0, 61.0, ("gamma gt", "gamma glutamyl transferase")),

    # ---------- Kidney/Renal Function Test (KFT/RFT) ----------
    BiomarkerRef("KFT", "Urea", "mg/dL", 17.0, 43.0, ("blood urea",)),
    BiomarkerRef("KFT", "BUN", "mg/dL", 7.0, 20.0, ("blood urea nitrogen",)),
    BiomarkerRef("KFT", "Creatinine", "mg/dL", 0.7, 1.3, ("s.creatinine", "serum creatinine"), "M"),
    BiomarkerRef("KFT", "Creatinine", "mg/dL", 0.6, 1.1, ("s.creatinine", "serum creatinine"), "F"),
    BiomarkerRef("KFT", "Uric Acid", "mg/dL", 3.5, 7.2, ("s.uric acid",), "M"),
    BiomarkerRef("KFT", "Uric Acid", "mg/dL", 2.6, 6.0, ("s.uric acid",), "F"),
    BiomarkerRef("KFT", "eGFR", "mL/min/1.73m2", 90.0, None, ("gfr", "estimated gfr")),

    # ---------- Lipid Profile ----------
    BiomarkerRef("Lipid Profile", "Total Cholesterol", "mg/dL", None, 200.0, ("cholesterol total", "t.cholesterol")),
    BiomarkerRef("Lipid Profile", "Triglycerides", "mg/dL", None, 150.0, ("tg", "trig")),
    BiomarkerRef("Lipid Profile", "HDL Cholesterol", "mg/dL", 40.0, None, ("hdl", "hdl-c")),
    BiomarkerRef("Lipid Profile", "LDL Cholesterol", "mg/dL", None, 100.0, ("ldl", "ldl-c")),
    BiomarkerRef("Lipid Profile", "VLDL Cholesterol", "mg/dL", 5.0, 40.0, ("vldl",)),
    BiomarkerRef("Lipid Profile", "Non-HDL Cholesterol", "mg/dL", None, 130.0, ("non hdl",)),
    BiomarkerRef("Lipid Profile", "Cholesterol/HDL Ratio", None, None, 5.0, ("chol hdl ratio",)),

    # ---------- Thyroid Profile ----------
    BiomarkerRef("Thyroid Profile", "TSH", "uIU/mL", 0.4, 4.0, ("thyroid stimulating hormone",)),
    BiomarkerRef("Thyroid Profile", "T3 Total", "ng/dL", 80.0, 200.0, ("total t3", "triiodothyronine")),
    BiomarkerRef("Thyroid Profile", "T4 Total", "ug/dL", 5.1, 14.1, ("total t4", "thyroxine")),
    BiomarkerRef("Thyroid Profile", "Free T3", "pg/mL", 2.0, 4.4, ("ft3",)),
    BiomarkerRef("Thyroid Profile", "Free T4", "ng/dL", 0.9, 1.7, ("ft4",)),

    # ---------- Blood Sugar ----------
    BiomarkerRef("Blood Sugar", "Fasting Blood Sugar", "mg/dL", 70.0, 100.0, ("fbs", "glucose fasting", "fasting glucose")),
    BiomarkerRef("Blood Sugar", "Postprandial Blood Sugar", "mg/dL", 70.0, 140.0, ("pp", "ppbs", "glucose pp", "post prandial")),
    BiomarkerRef("Blood Sugar", "Random Blood Sugar", "mg/dL", 70.0, 140.0, ("rbs", "glucose random")),
    BiomarkerRef("Blood Sugar", "HbA1c", "%", 4.0, 5.6, ("glycated hemoglobin", "a1c", "hba1c")),

    # ---------- Vitamin D ----------
    BiomarkerRef("Vitamin D", "Vitamin D (25-OH)", "ng/mL", 30.0, 100.0, ("25 hydroxy vitamin d", "25-oh vitamin d", "vit d")),

    # ---------- Vitamin B12 ----------
    BiomarkerRef("Vitamin B12", "Vitamin B12", "pg/mL", 211.0, 911.0, ("cobalamin", "vit b12", "b12")),

    # ---------- Iron Profile ----------
    BiomarkerRef("Iron Profile", "Serum Iron", "ug/dL", 65.0, 175.0, ("iron", "fe")),
    BiomarkerRef("Iron Profile", "TIBC", "ug/dL", 250.0, 450.0, ("total iron binding capacity",)),
    BiomarkerRef("Iron Profile", "Transferrin Saturation", "%", 20.0, 50.0, ("tsat", "transferrin sat")),
    BiomarkerRef("Iron Profile", "Ferritin", "ng/mL", 30.0, 400.0, ("s.ferritin",), "M"),
    BiomarkerRef("Iron Profile", "Ferritin", "ng/mL", 15.0, 150.0, ("s.ferritin",), "F"),

    # ---------- Uric Acid (standalone) ----------
    BiomarkerRef("Uric Acid", "Uric Acid", "mg/dL", 3.5, 7.2, ("s.uric acid",), "M"),
    BiomarkerRef("Uric Acid", "Uric Acid", "mg/dL", 2.6, 6.0, ("s.uric acid",), "F"),

    # ---------- Electrolytes ----------
    BiomarkerRef("Electrolytes", "Sodium", "mmol/L", 136.0, 145.0, ("na", "na+", "serum sodium")),
    BiomarkerRef("Electrolytes", "Potassium", "mmol/L", 3.5, 5.1, ("k", "k+", "serum potassium")),
    BiomarkerRef("Electrolytes", "Chloride", "mmol/L", 98.0, 107.0, ("cl", "cl-", "serum chloride")),
    BiomarkerRef("Electrolytes", "Bicarbonate", "mmol/L", 22.0, 29.0, ("hco3", "co2")),
    BiomarkerRef("Electrolytes", "Calcium", "mg/dL", 8.6, 10.3, ("ca", "serum calcium")),
    BiomarkerRef("Electrolytes", "Phosphorus", "mg/dL", 2.5, 4.5, ("po4", "phosphate")),
    BiomarkerRef("Electrolytes", "Magnesium", "mg/dL", 1.7, 2.2, ("serum magnesium",)),
]
# fmt: on


def all_aliases() -> dict[str, list[BiomarkerRef]]:
    """Map every canonical name and alias (lowercased) to its reference entries.

    A name can map to multiple entries when it is sex-specific (M/F variants).
    """
    index: dict[str, list[BiomarkerRef]] = {}
    for ref in REFERENCE_TABLE:
        keys = {ref.canonical.lower(), *(a.lower() for a in ref.aliases)}
        for key in keys:
            index.setdefault(key, []).append(ref)
    return index
