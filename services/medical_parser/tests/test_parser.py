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
