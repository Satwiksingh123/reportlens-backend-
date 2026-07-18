"""Curated medical knowledge base for grounding LLM explanations.

Each entry is a short, general, educational note about a biomarker: what it measures and
what low/high readings can *generally* relate to, plus non-drug lifestyle context where
appropriate. Notes are deliberately non-diagnostic and non-prescriptive.

`biomarker` matches the canonical names emitted by medical_parser so notes can be
retrieved by test name. `source` names the kind of public reference the note is aligned
with (e.g. MedlinePlus, WHO/ICMR guidance) — these are educational public-health sources,
not a substitute for clinical judgement.

NOTE: this content is written for a portfolio/educational tool and should be reviewed by
a qualified clinician before any real-world use.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class KBDoc:
    id: str
    biomarker: str | None  # canonical name from medical_parser, or None for panel-level
    panel: str
    text: str
    source: str


KNOWLEDGE_BASE: list[KBDoc] = [
    # ---------------- CBC ----------------
    KBDoc("cbc-hb", "Hemoglobin", "CBC",
          "Hemoglobin is the protein in red blood cells that carries oxygen around the body. "
          "A low hemoglobin level is called anaemia and can relate to low iron, vitamin B12 or "
          "folate, blood loss, or long-term illness. Iron-rich foods such as leafy greens, "
          "legumes, and (for non-vegetarians) lean red meat can support healthy levels. Very "
          "high values are less common and can relate to dehydration or other conditions.",
          "MedlinePlus"),
    KBDoc("cbc-wbc", "WBC Count", "CBC",
          "The white blood cell count reflects the immune cells that fight infection. A high "
          "count often accompanies infection, inflammation, or stress; a low count can relate "
          "to certain viral infections or effects on the bone marrow. A single reading is best "
          "interpreted alongside symptoms and other results.",
          "MedlinePlus"),
    KBDoc("cbc-plt", "Platelet Count", "CBC",
          "Platelets help blood clot. A low platelet count can increase bruising or bleeding, "
          "while a high count can relate to inflammation or, less often, bone-marrow conditions. "
          "Trends over time are more informative than one value.",
          "MedlinePlus"),
    KBDoc("cbc-mcv", "MCV", "CBC",
          "MCV describes the average size of red blood cells. Small cells (low MCV) often "
          "accompany iron-deficiency anaemia; large cells (high MCV) can relate to vitamin B12 "
          "or folate deficiency. It helps explain the *type* of anaemia when hemoglobin is low.",
          "MedlinePlus"),

    # ---------------- LFT ----------------
    KBDoc("lft-alt", "SGPT (ALT)", "LFT",
          "ALT (SGPT) is an enzyme found mainly in the liver. Raised ALT can indicate the liver "
          "is under stress from causes such as fatty liver, alcohol, certain medicines, or "
          "infection. Reducing alcohol, maintaining a healthy weight, and a balanced diet support "
          "liver health. Mild elevations are common and best reviewed with a doctor.",
          "MedlinePlus"),
    KBDoc("lft-ast", "SGOT (AST)", "LFT",
          "AST (SGOT) is an enzyme present in the liver and muscles. It is often interpreted "
          "together with ALT; a raised level can relate to liver stress or, sometimes, muscle "
          "activity. Context and the AST/ALT pattern matter for interpretation.",
          "MedlinePlus"),
    KBDoc("lft-bili", "Bilirubin Total", "LFT",
          "Bilirubin is a yellow pigment from the normal breakdown of red blood cells, processed "
          "by the liver. Higher levels can cause yellowing of the eyes or skin (jaundice) and can "
          "relate to how the liver is processing bilirubin. Mild isolated elevations are sometimes "
          "harmless (e.g. Gilbert's pattern) but should be reviewed.",
          "MedlinePlus"),
    KBDoc("lft-alb", "Albumin", "LFT",
          "Albumin is a protein made by the liver that helps maintain fluid balance and carries "
          "substances in the blood. Low albumin can relate to liver or kidney conditions, poor "
          "nutrition, or inflammation. Adequate dietary protein supports healthy levels.",
          "MedlinePlus"),

    # ---------------- KFT ----------------
    KBDoc("kft-creat", "Creatinine", "KFT",
          "Creatinine is a waste product filtered by the kidneys. A higher level can suggest the "
          "kidneys are filtering less efficiently, though it is also affected by muscle mass and "
          "hydration. Staying well hydrated and managing blood pressure and blood sugar supports "
          "kidney health.",
          "MedlinePlus"),
    KBDoc("kft-urea", "Urea", "KFT",
          "Blood urea is a waste product from protein breakdown, cleared by the kidneys. It can "
          "rise with reduced kidney filtration, dehydration, or a high-protein state, and is "
          "interpreted together with creatinine.",
          "MedlinePlus"),
    KBDoc("kft-egfr", "eGFR", "KFT",
          "eGFR estimates how well the kidneys filter blood, calculated from creatinine. A higher "
          "eGFR is better; a low eGFR suggests reduced kidney function and is best monitored over "
          "time with a doctor. Blood-pressure and blood-sugar control help protect kidney function.",
          "WHO/ICMR"),

    # ---------------- Lipid Profile ----------------
    KBDoc("lipid-ldl", "LDL Cholesterol", "Lipid Profile",
          "LDL is often called 'bad' cholesterol because higher levels are associated with "
          "build-up in arteries over time. Diets lower in saturated and trans fats, higher in "
          "fibre, and regular physical activity are evidence-based ways to support healthier LDL "
          "levels.",
          "WHO"),
    KBDoc("lipid-hdl", "HDL Cholesterol", "Lipid Profile",
          "HDL is often called 'good' cholesterol; higher levels are generally favourable. Regular "
          "exercise, avoiding smoking, and healthy fats (e.g. nuts, olive oil, fish) are associated "
          "with better HDL.",
          "WHO"),
    KBDoc("lipid-tg", "Triglycerides", "Lipid Profile",
          "Triglycerides are a type of fat in the blood. High levels are associated with excess "
          "refined carbohydrate and alcohol intake and with overweight. Reducing sugary foods and "
          "alcohol and increasing activity can help lower them.",
          "WHO"),
    KBDoc("lipid-tc", "Total Cholesterol", "Lipid Profile",
          "Total cholesterol combines LDL, HDL, and part of triglycerides. It is best interpreted "
          "with its components and overall heart-disease risk factors rather than alone.",
          "WHO"),

    # ---------------- Thyroid ----------------
    KBDoc("thy-tsh", "TSH", "Thyroid Profile",
          "TSH is the pituitary hormone that signals the thyroid. A high TSH usually suggests an "
          "underactive thyroid (hypothyroidism), while a low TSH can suggest an overactive thyroid. "
          "It is the most common first-line thyroid test and is interpreted with T3/T4 and symptoms.",
          "MedlinePlus"),
    KBDoc("thy-ft4", "Free T4", "Thyroid Profile",
          "Free T4 is the active thyroid hormone available to tissues. It is interpreted together "
          "with TSH to understand thyroid function.",
          "MedlinePlus"),

    # ---------------- Blood Sugar ----------------
    KBDoc("sugar-fbs", "Fasting Blood Sugar", "Blood Sugar",
          "Fasting blood sugar is measured after not eating for several hours. Higher values can "
          "relate to impaired glucose regulation or diabetes and are confirmed with repeat testing "
          "and HbA1c. A balanced diet, weight management, and activity support healthy glucose.",
          "WHO"),
    KBDoc("sugar-hba1c", "HbA1c", "Blood Sugar",
          "HbA1c reflects average blood sugar over roughly the past 2-3 months. It is used to "
          "screen for and monitor diabetes because it is less affected by a single meal. Dietary "
          "changes and physical activity are first-line, evidence-based ways to improve it.",
          "WHO"),

    # ---------------- Vitamins ----------------
    KBDoc("vitd", "Vitamin D (25-OH)", "Vitamin D",
          "Vitamin D supports bone health and immune function. Low levels are very common and can "
          "relate to limited sun exposure and low dietary intake. Safe sunlight, fortified foods, "
          "and, where advised by a doctor, supplementation can help restore levels.",
          "MedlinePlus"),
    KBDoc("vitb12", "Vitamin B12", "Vitamin B12",
          "Vitamin B12 is needed for nerve function and red blood cell formation. Low levels can "
          "cause tiredness, tingling, or a specific type of anaemia, and are more common in strict "
          "vegetarian/vegan diets. B12-rich or fortified foods, or supplements when advised, can help.",
          "MedlinePlus"),

    # ---------------- Iron ----------------
    KBDoc("iron-ferritin", "Ferritin", "Iron Profile",
          "Ferritin reflects the body's stored iron. Low ferritin is an early sign of iron "
          "deficiency, often before anaemia appears; high ferritin can relate to inflammation or "
          "iron overload. It is interpreted with the rest of the iron studies.",
          "MedlinePlus"),

    # ---------------- Uric Acid ----------------
    KBDoc("uric", "Uric Acid", "Uric Acid",
          "Uric acid is a waste product; high levels can crystallise in joints and are associated "
          "with gout. Reducing high-purine foods (e.g. organ meats, some seafood) and alcohol, and "
          "staying hydrated, can help lower it.",
          "MedlinePlus"),

    # ---------------- Electrolytes ----------------
    KBDoc("elec-na", "Sodium", "Electrolytes",
          "Sodium helps regulate fluid balance and nerve/muscle function. Abnormal levels usually "
          "reflect the body's water balance (e.g. dehydration or fluid retention) rather than "
          "dietary salt alone and should be interpreted by a doctor.",
          "MedlinePlus"),
    KBDoc("elec-k", "Potassium", "Electrolytes",
          "Potassium is essential for heart and muscle function. Both low and high potassium can "
          "affect the heart rhythm, so abnormal values are reviewed promptly with a clinician. "
          "Some kidney conditions and medicines affect potassium levels.",
          "MedlinePlus"),

    # ---------------- Panel-level fallbacks ----------------
    KBDoc("panel-cbc", None, "CBC",
          "A Complete Blood Count measures red cells, white cells, and platelets, giving a broad "
          "picture of general health, anaemia, infection, and clotting capacity.",
          "MedlinePlus"),
    KBDoc("panel-lft", None, "LFT",
          "A Liver Function Test panel looks at enzymes and proteins that reflect how the liver is "
          "working and whether it is under stress.",
          "MedlinePlus"),
]
