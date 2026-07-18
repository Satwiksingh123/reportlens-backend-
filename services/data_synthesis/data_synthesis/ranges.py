"""Load the canonical reference table from the medical_parser package.

In a monorepo the clean way is to `pip install -e services/medical_parser`. To keep
this generator runnable straight from a checkout (and in CI without an install step),
we also fall back to adding the sibling package to sys.path.
"""

import sys
from pathlib import Path

try:
    from medical_parser.reference_ranges import REFERENCE_TABLE, BiomarkerRef
except ModuleNotFoundError:  # pragma: no cover - path bootstrap for uninstalled checkout
    _sibling = Path(__file__).resolve().parents[2] / "medical_parser"
    sys.path.insert(0, str(_sibling))
    from medical_parser.reference_ranges import REFERENCE_TABLE, BiomarkerRef

__all__ = ["REFERENCE_TABLE", "BiomarkerRef", "panel_names", "panel_biomarkers"]


def panel_names() -> list[str]:
    seen: list[str] = []
    for ref in REFERENCE_TABLE:
        if ref.panel not in seen:
            seen.append(ref.panel)
    return seen


def panel_biomarkers(panel: str, sex: str) -> list[BiomarkerRef]:
    """Return one reference entry per canonical biomarker in a panel, choosing the
    entry that matches `sex` when sex-specific variants exist."""
    by_name: dict[str, BiomarkerRef] = {}
    for ref in REFERENCE_TABLE:
        if ref.panel != panel:
            continue
        current = by_name.get(ref.canonical)
        if current is None:
            by_name[ref.canonical] = ref
        elif ref.sex == sex:
            by_name[ref.canonical] = ref  # sex-matched variant wins
    return list(by_name.values())
