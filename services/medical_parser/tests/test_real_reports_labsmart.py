"""End-to-end value accuracy on 4 real Labsmart sample reports (a third, independent
lab-software vendor) - a regression guard for the whole parser pipeline against a
template/vocabulary the parser was never tuned against directly. See
fixtures_labsmart.py for provenance and sample_reports/README.md for source URLs.
"""

import pytest
from fixtures_labsmart import LABSMART_REPORTS

from medical_parser import parse_report


def _norm(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


@pytest.mark.parametrize("name", sorted(LABSMART_REPORTS))
def test_labsmart_report_100_percent_value_accuracy(name):
    text, gt = LABSMART_REPORTS[name]
    got = {r.test_name: r.value for r in parse_report(text)}

    missing = [n for n in gt if got.get(n) is None]
    wrong = [
        f"{n}: got {got[n]!r}, expected {expected!r}"
        for n, expected in gt.items()
        if got.get(n) is not None and _norm(got[n]) != _norm(expected)
    ]

    assert not wrong, f"wrong values (must be zero): {wrong}"
    assert not missing, f"missing values: {missing}"
