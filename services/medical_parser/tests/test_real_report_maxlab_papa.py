"""End-to-end value accuracy on a real, hand-verified 11-page Max Lab report (9 panels,
personal data stripped) - a regression guard against the whole parser pipeline, not just
individual alias rules. See fixtures_maxlab_papa.py for provenance and scope notes.
"""

from fixtures_maxlab_papa import MAXLAB_PAPA_GT, MAXLAB_PAPA_TEXT

from medical_parser import parse_report


def _norm(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def test_maxlab_papa_report_100_percent_value_accuracy():
    got = {r.test_name: r.value for r in parse_report(MAXLAB_PAPA_TEXT)}

    missing = [name for name in MAXLAB_PAPA_GT if got.get(name) is None]
    wrong = [
        f"{name}: got {got[name]!r}, expected {expected!r}"
        for name, expected in MAXLAB_PAPA_GT.items()
        if got.get(name) is not None and _norm(got[name]) != _norm(expected)
    ]

    assert not wrong, f"wrong values (must be zero): {wrong}"
    assert not missing, f"missing values: {missing}"
    assert len(got) >= len(MAXLAB_PAPA_GT)
