"""Adapter that runs the medical_parser package on raw OCR text.

The parser lives in services/medical_parser. In the Docker image it is pip-installed;
for a plain checkout we fall back to adding the sibling package to sys.path so the API
runs without an extra install step.
"""

import sys
from pathlib import Path

try:
    from medical_parser import parse_report
except ModuleNotFoundError:  # pragma: no cover - path bootstrap for uninstalled checkout
    _pkg = Path(__file__).resolve().parents[3] / "medical_parser"
    sys.path.insert(0, str(_pkg))
    from medical_parser import parse_report


def parse(raw_text: str, sex: str | None = None) -> list[dict]:
    return [b.to_dict() for b in parse_report(raw_text, sex=sex)]
