"""End-to-end value accuracy on 5 real MyLab India sample reports (a 5th independent
lab-software vendor). See fixtures_mylab.py for provenance, the one known/documented
limitation (Bilirubin Total, intentionally excluded from ground truth here), and
sample_reports/README.md for source URLs.
"""

import pytest
from fixtures_mylab import MYLAB_REPORTS

from medical_parser import parse_report


def _norm(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


@pytest.mark.parametrize("name", sorted(MYLAB_REPORTS))
def test_mylab_report_value_accuracy(name):
    text, gt = MYLAB_REPORTS[name]
    got = {r.test_name: r.value for r in parse_report(text)}

    missing = [n for n in gt if got.get(n) is None]
    wrong = [
        f"{n}: got {got[n]!r}, expected {expected!r}"
        for n, expected in gt.items()
        if got.get(n) is not None and _norm(got[n]) != _norm(expected)
    ]

    assert not wrong, f"wrong values (must be zero): {wrong}"
    assert not missing, f"missing values: {missing}"
