from data_synthesis.generator import generate_report, render_report


def test_deterministic_with_seed():
    a = generate_report(seed=42)
    b = generate_report(seed=42)
    assert a.to_ground_truth() == b.to_ground_truth()


def test_report_has_rows_and_status():
    r = generate_report(panel="CBC", sex="M", seed=1)
    assert r.panel == "CBC"
    assert r.rows
    for row in r.rows:
        assert row.status in {"Low", "Normal", "High"}
        assert row.value


def test_text_lines_contain_biomarkers():
    r = generate_report(panel="Lipid Profile", seed=3)
    joined = "\n".join(r.text_lines)
    assert "Total Cholesterol" in joined


def test_render_produces_image_and_boxes():
    r = generate_report(panel="Thyroid Profile", seed=5)
    img, boxes = render_report(r, add_noise=False, seed=5)
    assert img.size[0] > 0 and img.size[1] > 0
    assert boxes and all("box" in b and "text" in b for b in boxes)


def test_ground_truth_status_matches_reference_table():
    """The generator's declared status must equal what the parser derives from the
    same text — this is the self-consistency guarantee that makes the data usable."""
    from medical_parser import parse_report

    r = generate_report(panel="CBC", sex="M", seed=7)
    text = "\n".join(r.text_lines)
    parsed = {p.test_name: p.status for p in parse_report(text, sex="M")}
    for row in r.rows:
        # Every biomarker the parser recognised should agree on status.
        if row.test_name in parsed:
            assert parsed[row.test_name] == row.status, row.test_name
