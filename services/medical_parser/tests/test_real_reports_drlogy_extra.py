"""End-to-end value accuracy on 2 more real Drlogy sample reports (Electrolytes panel,
Vitamin B12) that fill panel-coverage gaps. See fixtures_drlogy_electrolytes_vitb12.py.
"""

import pytest
from fixtures_drlogy_electrolytes_vitb12 import DRLOGY_EXTRA_REPORTS

from medical_parser import parse_report


def _norm(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


@pytest.mark.parametrize("name", sorted(DRLOGY_EXTRA_REPORTS))
def test_drlogy_extra_report_100_percent_value_accuracy(name):
    text, gt = DRLOGY_EXTRA_REPORTS[name]
    got = {r.test_name: r.value for r in parse_report(text)}

    missing = [n for n in gt if got.get(n) is None]
    wrong = [
        f"{n}: got {got[n]!r}, expected {expected!r}"
        for n, expected in gt.items()
        if got.get(n) is not None and _norm(got[n]) != _norm(expected)
    ]

    assert not wrong, f"wrong values (must be zero): {wrong}"
    assert not missing, f"missing values: {missing}"
