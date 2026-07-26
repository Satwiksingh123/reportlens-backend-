from medical_parser import parse_report
from medical_parser.parser import classify_status, parse_line


def test_basic_cbc_line_low():
    p = parse_line("Hemoglobin 11.2 g/dL 13.0-17.0")
    assert p is not None
    assert p.test_name == "Hemoglobin"
    assert p.value == "11.2"
    assert p.unit == "g/dL"
    assert p.reference_range == "13.0-17.0"
    assert p.status == "Low"


def test_high_value():
    p = parse_line("WBC 13000 /uL 4000-11000")
    assert p.test_name == "WBC Count"
    assert p.value == "13000"
    assert p.status == "High"


def test_normal_value():
    p = parse_line("Platelets 250000 /uL 150000-410000")
    assert p.status == "Normal"


def test_thousands_separator_value():
    # Western grouping should parse cleanly.
    p2 = parse_line("Platelet Count 210,000 /uL 150000-410000")
    assert p2.value == "210000"
    assert p2.status == "Normal"


def test_name_with_digits_not_taken_as_value():
    # 'T3' and '25' inside names must not be read as the measured value.
    p = parse_line("Free T3 3.1 pg/mL 2.0-4.4")
    assert p.test_name == "Free T3"
    assert p.value == "3.1"
    assert p.status == "Normal"

    p2 = parse_line("Vitamin D (25-OH) 22 ng/mL 30-100")
    assert p2.test_name == "Vitamin D (25-OH)"
    assert p2.value == "22"
    assert p2.status == "Low"


def test_hba1c():
    p = parse_line("HbA1c 6.4 % 4.0-5.6")
    assert p.test_name == "HbA1c"
    assert p.value == "6.4"
    assert p.status == "High"


def test_one_sided_upper_range_printed():
    p = parse_line("Total Cholesterol 240 mg/dL <200")
    assert p.test_name == "Total Cholesterol"
    assert p.reference_range == "<200"
    assert p.status == "High"


def test_one_sided_lower_range_hdl():
    p = parse_line("HDL Cholesterol 55 mg/dL >40")
    assert p.reference_range == ">40"
    assert p.status == "Normal"


def test_fallback_range_when_not_printed():
    # No printed range -> uses canonical table.
    p = parse_line("TSH 8.0 uIU/mL")
    assert p.reference_range == "0.4-4"
    assert p.status == "High"


def test_sex_specific_fallback():
    male = parse_line("Hemoglobin 13.5 g/dL", sex="M")
    female = parse_line("Hemoglobin 13.5 g/dL", sex="F")
    assert male.status == "Normal"   # 13.0-17.0
    assert female.status == "Normal"  # 12.0-15.0
    low_male = parse_line("Hemoglobin 12.5 g/dL", sex="M")
    assert low_male.status == "Low"


def test_unknown_line_returns_none():
    assert parse_line("Patient Name: John Doe") is None
    assert parse_line("Collected on 2026-07-18") is None


def test_classify_status_edges():
    assert classify_status(None, 1, 2) is None
    assert classify_status(5, None, None) is None
    assert classify_status(5, None, 10) == "Normal"
    assert classify_status(15, None, 10) == "High"


def test_parse_report_dedup_and_multiline():
    text = """
    Complete Blood Count (CBC)
    Hemoglobin 11.2 g/dL 13.0-17.0
    WBC 11500 /uL 4000-11000
    Platelets 210000 /uL 150000-410000
    Hemoglobin 11.2 g/dL 13.0-17.0
    """
    rows = parse_report(text)
    names = [r.test_name for r in rows]
    assert names.count("Hemoglobin") == 1
    assert "WBC Count" in names
    assert "Platelet Count" in names


# --- regressions found by testing against real (publicly published sample) lab reports ---


def test_dedup_prefers_valued_row_over_bare_heading():
    # Some real report layouts print a bare section heading (no number) before the
    # actual data row. Keeping only the first match would silently keep the heading
    # and drop the real value.
    text = """
    HEMOGLOBIN
    Hemoglobin (Hb) 12.5 Low 13.0-17.0 g/dL
    """
    rows = parse_report(text)
    hb = next(r for r in rows if r.test_name == "Hemoglobin")
    assert hb.value == "12.5"
    assert hb.status == "Low"


def test_t3_t4_reversed_comma_order():
    # Real reports print "T3, TOTAL" (reversed word order + comma) rather than our
    # "total t3" phrase alias.
    p3 = parse_line("T3, TOTAL 350.00 High 80.00 - 200.00 ng/dL")
    assert p3.test_name == "T3 Total"
    assert p3.value == "350.00"
    assert p3.status == "High"

    p4 = parse_line("T4, TOTAL 28.50 High 4.50 - 12.50 mcg/dL")
    assert p4.test_name == "T4 Total"
    assert p4.value == "28.50"


def test_cholesterol_hdl_ratio_not_confused_with_total_cholesterol():
    # "Total Cholesterol/HDL Ratio" contains "total cholesterol" as a true substring;
    # it must match the ratio biomarker, not plain Total Cholesterol.
    p = parse_line("Total Cholesterol/HDL 6.2 0.0-4.9")
    assert p.test_name == "Cholesterol/HDL Ratio"
    assert p.value == "6.2"


def test_range_lower_bound_is_never_reported_as_the_measured_value():
    """When OCR drops the value column, the range's own first number must not become the
    result. Found by running the pipeline on simulated phone photos: three biomarkers came
    back with their reference range's lower bound as the "measurement" (T3 80.00 instead of
    350.00, T4 4.50 instead of 28.50, RBC 4.50 instead of 6.50) - wrong values, not misses,
    which is the one failure mode this project must not have.
    """
    for line in [
        "T3, TOTAL 80.00 - 200.00 ng/dL",
        "T4, TOTAL 4.50 - 12.50 mcg/dL",
        "Total RBC count 4.50 - 5.50 mill/cumm",
    ]:
        p = parse_line(line)
        assert p is not None, line
        assert p.value is None, f"{line!r} fabricated value {p.value!r} from its own range"
        assert p.status is None


def test_value_equal_to_its_range_bound_still_parses():
    # The guard must not reject a genuine measurement that coincides with a range bound -
    # this exact row appears in a real report.
    p = parse_line("Hemoglobin (Hb) 13.00 Normal 13.00 - 17.00 g/dL")
    assert p.value == "13.00"
    assert p.status == "Normal"


def test_one_sided_ranges_still_extract_their_value():
    assert parse_line("Cholesterol 192 mg/dL < 200").value == "192"
    assert parse_line("HDL Cholesterol 31.0 mg/dL > 40").value == "31.0"


def test_native_value_beats_merged_value_regardless_of_order():
    # Real bug: a heading with no value on its own line ("VITAMIN B12 (CYANOCOBALAMIN)")
    # triggers continuation-merge, which can absorb an unrelated stray number from
    # boilerplate BEFORE the real result line appears ("Sample Type Serum (3 ml)..." has a
    # "3"). The later, same-line ("native") reading must win even though it comes second.
    text = (
        "VITAMIN B12 (CYANOCOBALAMIN)\n"
        "Sample Type Serum (3 ml) TAT: 2hrs (Normal: 1 - 3 hrs)\n"
        "VITAMIN B12 (CYANOCOBALAMIN) 452.00 Normal 200.00 - 900.00 pg/mL\n"
    )
    rows = {r.test_name: r.value for r in parse_report(text)}
    assert rows.get("Vitamin B12") == "452.00"


def test_bare_short_alias_never_fabricates_value_from_unrelated_text():
    # Real bug found via a real report: "K" (Potassium) and "Fe" (Serum Iron) matched
    # inside a doctor's name initial and OCR noise near a logo, with no number on that
    # line - the continuation-merge must NOT go hunting down the page for a value to
    # attach to these bare short aliases (a signature block, a page number, anything
    # else nearby could otherwise be fabricated into a fake medical result).
    text = "Mr. Sachin Sharma Dr. A. K. Asthana\nDMLT, Lab Incharge Page 1 of 2"
    rows = parse_report(text)
    potassium = next((r for r in rows if r.test_name == "Potassium"), None)
    # a spurious match is tolerable (it may still surface with no value); a FABRICATED
    # value borrowed from unrelated nearby text (e.g. "Page 1 of 2") is not.
    assert potassium is None or potassium.value is None


def test_pending_test_not_fabricated_as_a_result():
    # A number appearing near a "not yet received" style note must not be turned into
    # a fake result (with a fake Low/High status) for a test that was never actually run.
    line = "Blood Sugar - Post Prandial (Glucose PP), 2 Hrs : Sample not yet received"
    assert parse_line(line) is None

    text = f"""
    Cholesterol 192 mg/dL < 200
    {line}
    """
    rows = parse_report(text)
    assert "Postprandial Blood Sugar" not in [r.test_name for r in rows]


def test_bare_cholesterol_label_matches_total_cholesterol():
    # Some reports print just "Cholesterol", not "Total Cholesterol".
    p = parse_line("Cholesterol 192 mg/dL < 200")
    assert p.test_name == "Total Cholesterol"
    assert p.value == "192"
    assert p.status == "Normal"


def test_rdw_ocr_misread_as_row():
    # Tesseract reads "RDW" as "ROW" on real reports (D/W glyphs); must still match.
    p = parse_line("ROW 12.00 Normal 11.60 - 14.00 %")
    assert p.test_name == "RDW"
    assert p.value == "12.00"
    assert p.status == "Normal"


def test_triglyceride_singular():
    p = parse_line("Triglyceride 143.0 mg/dL < 150")
    assert p.test_name == "Triglycerides"
    assert p.value == "143.0"


def test_alkaline_phosphatase_with_mangled_name():
    # Real OCR: "Alkaline Phosphatase (ALP)" -> "Alkaline: Rhespliatase (ALF)".
    p = parse_line("Alkaline: Rhespliatase (ALF) 45.00 Normal 30.00 - 120.00 U/L")
    assert p.test_name == "Alkaline Phosphatase"
    assert p.value == "45.00"


def test_value_on_following_line_is_merged():
    # OCR sometimes splits a test's name and value across lines (the method sub-label
    # carries the value): "MCH" then "Calculated 35 High 27 - 32 pg".
    text = "MCH\nCalculated 35 High 27 - 32 pg\nMCHC 33.0 Normal 32.5 - 34.5 g/dL"
    rows = {r.test_name: r.value for r in parse_report(text)}
    assert rows.get("MCH") == "35"
    assert rows.get("MCHC") == "33.0"


def test_dot_separated_abbreviations_match():
    # A real vendor (MyLab India) prints a dot after every letter of the abbreviation.
    assert parse_line("S.G.O.T. 48.6 U/L Up to 46 U/L").test_name == "SGOT (AST)"
    assert parse_line("S.G.P.T. 51.3 IU/L Up to 49 U/L").test_name == "SGPT (ALT)"
    assert parse_line("G.G.T.P 28 IU/L 25 - 43 IU/L").test_name == "GGT"


def test_plural_wording_matches_singular_alias():
    # Real reports sometimes pluralize a test name ("Total Proteins", "S.CHLORIDES").
    assert parse_line("Total Proteins 7.2 gm/dl 6.0-8.3").test_name == "Total Protein"
    assert parse_line("S.CHLORIDES 21.5 mEq/L 98-107").test_name == "Chloride"


def test_punctuation_variants_match_across_labs():
    # Real labs punctuate the same test differently than our phrase aliases; matching
    # must be robust to parens/dots/commas between the same words.
    assert parse_line("Bilirubin (Total) 1.58 mg/dl 0.3 - 1.2").test_name == "Bilirubin Total"
    assert parse_line("A.G. ratio 1.9 1.2 - 1.5").test_name == "A/G Ratio"
    assert parse_line("Glucose (Fasting) 94.3 mg/dl 74 - 99").test_name == "Fasting Blood Sugar"
    assert parse_line("25 Hydroxy, Vitamin D 6.7 ng/mL 30-100").test_name == "Vitamin D (25-OH)"


def test_value_not_read_from_glued_abbreviation_in_heading():
    # A title line repeating the test's own abbreviation ("Vit- B12") must not have that
    # abbreviation's digits mistaken for a measured value.
    p = parse_line("Vitamin B12 (Vit- B12) (Cyanocobalamin)")
    assert p.value is None


def test_mch_mchc_not_confused_with_plain_hemoglobin():
    # "MEAN CELL HAEMOGLOBIN, MCH" / "... CON, MCHC" both contain the word "Haemoglobin"
    # (Hemoglobin's own alias) - MCH/MCHC's aliases must be specific enough to win.
    mch = parse_line("MEAN CELL HAEMOGLOBIN, MCH 30.0 Pg 27 - 32")
    assert mch.test_name == "MCH"
    assert mch.value == "30.0"

    mchc = parse_line("MEAN CELL HAEMOGLOBIN CON, MCHC 35.7 % 31.5 - 34.5")
    assert mchc.test_name == "MCHC"
    assert mchc.value == "35.7"
    assert mchc.status == "High"


def test_hba1c_not_confused_with_plain_hemoglobin():
    # "Glycosylated Haemoglobin(Hb A1c)" contains the word "Haemoglobin" (the CBC test's
    # own alias) - HbA1c's aliases must be specific enough to win.
    p = parse_line("Glycosylated Haemoglobin(Hb A1c) 5.60 % < 5.7")
    assert p.test_name == "HbA1c"
    assert p.value == "5.60"


def test_two_column_label_then_value_merged():
    # A detached two-column layout: label, value, printed range on separate lines.
    text = "Triglycerides\n100.00\n< 150.00\nHDL Cholesterol\n50.00"
    rows = {r.test_name: r.value for r in parse_report(text)}
    assert rows.get("Triglycerides") == "100.00"
    assert rows.get("HDL Cholesterol") == "50.00"
