"""Rule-based medical lab report parser.

Pipeline per line of OCR text:
  1. Extract a numeric measured value and (optionally) a unit and a printed range.
  2. Match the leading text to a known biomarker via the alias index.
  3. Choose a reference range: the one printed on the report wins; otherwise fall
     back to the canonical table (sex-aware).
  4. Classify status as Low / Normal / High (handling one-sided ranges).

This deterministic layer handles the well-structured majority of lines. A learned
NER model (see ner.py) is layered on top later to catch messy/irregular layouts the
rules miss; the rules remain the ground-truth-checked backbone.
"""

import re
from dataclasses import asdict, dataclass

from medical_parser.reference_ranges import BiomarkerRef, all_aliases

_ALIAS_INDEX = all_aliases()

# Precompile a boundary-aware matcher per alias key so short abbreviations (na, k, cl,
# hb) match only as standalone tokens, never as substrings of ordinary words like
# "Name" or "kidney". Boundaries are non-alphanumeric (so "na+" / "hdl-c" still work).
_KEY_PATTERNS: list[tuple[str, re.Pattern]] = sorted(
    (
        (key, re.compile(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])"))
        for key in _ALIAS_INDEX
    ),
    key=lambda kv: len(kv[0]),
    reverse=True,
)

# A measured value: 210,000 (grouped) OR 210000 / 11.2 (plain). The grouped form is
# listed first and requires at least one comma group, so a plain "13000" is not
# truncated to "130" by the grouped alternative.
_NUM = r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[-+]?\d+(?:\.\d+)?"

# Printed reference range variants: "13.0-17.0", "13 to 17", "< 200", "> 40"
_RANGE_INTERVAL = re.compile(
    rf"(?P<low>{_NUM})\s*(?:-|–|to)\s*(?P<high>{_NUM})"
)
_RANGE_UPPER = re.compile(rf"[<≤]\s*(?P<high>{_NUM})")
_RANGE_LOWER = re.compile(rf"[>≥]\s*(?P<low>{_NUM})")

# Phrases indicating a test was requested but has no actual result yet. Real reports
# routinely include a line like "Blood Sugar - PP, 2 Hrs : Sample not yet received" -
# without this guard, a stray number nearby (here "2 Hrs") would be fabricated into a
# fake result (and even a fake Low/High status), which is unacceptable for a medical tool.
_NO_RESULT_PHRASES = (
    "not yet received", "not received", "sample rejected", "sample not collected",
    "quantity not sufficient", "qns", "results awaited", "result awaited",
    "not performed", "not done", "test cancelled", "sample pending",
)


def _has_no_result(line: str) -> bool:
    lowered = line.lower()
    return any(phrase in lowered for phrase in _NO_RESULT_PHRASES)


# Units we recognise, longest first so "mg/dL" wins over "dL".
_UNITS = sorted(
    [
        "million/uL", "/uL", "g/dL", "mg/dL", "ug/dL", "ng/dL", "pg/mL", "ng/mL",
        "uIU/mL", "mIU/L", "U/L", "mmol/L", "umol/L", "mL/min/1.73m2", "fL", "pg",
        "%", "ug/mL", "mEq/L",
    ],
    key=len,
    reverse=True,
)


@dataclass
class ParsedBiomarker:
    panel: str | None
    test_name: str
    value: str | None
    unit: str | None
    reference_range: str | None
    status: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def _to_float(raw: str) -> float | None:
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def _match_biomarker(name_part: str) -> tuple[list[BiomarkerRef], int] | None:
    """Return (matching reference entries, end index of the matched name in the line).

    Prefers the longest matching alias so 'total t3' beats 't3'. The end index lets
    the caller search for the measured value AFTER the name, so digits inside names
    (T3, B12, 25-OH, HbA1c) are never mistaken for the value.
    """
    text = name_part.lower()
    for key, pattern in _KEY_PATTERNS:  # already longest-first
        m = pattern.search(text)
        if m:
            return _ALIAS_INDEX[key], m.end()
    return None


def _pick_ref(refs: list[BiomarkerRef], sex: str | None) -> BiomarkerRef:
    if sex:
        for r in refs:
            if r.sex == sex:
                return r
    # no sex given: prefer a sex-neutral entry, else first
    for r in refs:
        if r.sex is None:
            return r
    return refs[0]


def _widened_interval(refs: list[BiomarkerRef]) -> tuple[float | None, float | None]:
    """When sex is unknown, widen to the union of M/F intervals to avoid false flags."""
    lows = [r.low for r in refs if r.low is not None]
    highs = [r.high for r in refs if r.high is not None]
    low = min(lows) if lows else None
    high = max(highs) if highs else None
    return low, high


def _extract_printed_range(text: str) -> tuple[float | None, float | None, str | None]:
    m = _RANGE_INTERVAL.search(text)
    if m:
        return _to_float(m["low"]), _to_float(m["high"]), f"{m['low']}-{m['high']}"
    m = _RANGE_UPPER.search(text)
    if m:
        return None, _to_float(m["high"]), f"<{m['high']}"
    m = _RANGE_LOWER.search(text)
    if m:
        return _to_float(m["low"]), None, f">{m['low']}"
    return None, None, None


def _extract_unit(text: str) -> str | None:
    for unit in _UNITS:
        if unit == "%":
            if "%" in text:
                return "%"
        elif unit.lower() in text.lower():
            return unit
    return None


def classify_status(
    value: float | None, low: float | None, high: float | None
) -> str | None:
    if value is None:
        return None
    if low is not None and value < low:
        return "Low"
    if high is not None and value > high:
        return "High"
    if low is None and high is None:
        return None
    return "Normal"


def parse_line(line: str, sex: str | None = None) -> ParsedBiomarker | None:
    if _has_no_result(line):
        return None
    match = _match_biomarker(line)
    if match is None:
        return None
    refs, name_end = match

    # The measured value is the first number that appears AFTER the biomarker name,
    # so digits embedded in the name are never picked up.
    tail = line[name_end:]
    value_match = re.search(_NUM, tail)
    value_raw = value_match.group(0) if value_match else None
    value = _to_float(value_raw) if value_raw else None

    unit = _extract_unit(line) or refs[0].unit

    p_low, p_high, printed = _extract_printed_range(line)
    if printed is not None:
        low, high, ref_str = p_low, p_high, printed
    elif sex:
        chosen = _pick_ref(refs, sex)
        low, high = chosen.low, chosen.high
        ref_str = _format_fallback(low, high)
    else:
        low, high = _widened_interval(refs)
        ref_str = _format_fallback(low, high)

    status = classify_status(value, low, high)
    return ParsedBiomarker(
        panel=refs[0].panel,
        test_name=refs[0].canonical,
        value=value_raw.replace(",", "") if value_raw else None,
        unit=unit,
        reference_range=ref_str,
        status=status,
    )


def _format_fallback(low: float | None, high: float | None) -> str | None:
    if low is not None and high is not None:
        return f"{_fmt(low)}-{_fmt(high)}"
    if high is not None:
        return f"<{_fmt(high)}"
    if low is not None:
        return f">{_fmt(low)}"
    return None


def _fmt(x: float) -> str:
    return str(int(x)) if x.is_integer() else str(x)


def _has_value_after_name(line: str) -> bool:
    """True if `line` matches a biomarker AND has a numeric value after the name."""
    m = _match_biomarker(line)
    return bool(m and re.search(_NUM, line[m[1] :]))


def _merge_continuation_lines(lines: list[str]) -> list[str]:
    """Re-join a biomarker whose value landed on a following line.

    Some layouts (and some OCR page-segmentation modes) put a test's name on one line
    and its value on the next - either the method sub-label carried the value
    ("MCH" / "Calculated 35 High 27 - 32 pg") or a two-column layout detached them
    ("Triglycerides" / "100.00" / "< 150.00"). When a biomarker-name line has no value,
    absorb following non-biomarker lines until (and including) the first one bearing a
    number, stopping early if the next line is itself a different biomarker.
    """
    merged: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _match_biomarker(line) and not _has_value_after_name(line):
            combined = line
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if _match_biomarker(nxt):  # a different biomarker starts; don't cross it
                    break
                combined += " " + nxt
                j += 1
                if re.search(_NUM, nxt):  # absorbed the value; stop
                    break
            merged.append(combined)
            i = j
        else:
            merged.append(line)
            i += 1
    return merged


def parse_report(raw_text: str, sex: str | None = None) -> list[ParsedBiomarker]:
    """Parse full OCR text into structured biomarkers.

    De-duplicates by canonical test name, preferring the first occurrence that has an
    actual measured value. Some real report layouts print the test name twice: once as
    a bare section heading (e.g. "HEMOGLOBIN", no number) and again on the real data row
    ("Hemoglobin (Hb) 12.5 Low 13.0-17.0 g/dL"). Naively keeping only the very first
    match would silently keep the valueless heading and drop the real result. A
    continuation-line merge first re-joins values that OCR split onto the next line.
    """
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    lines = _merge_continuation_lines(lines)

    by_name: dict[str, ParsedBiomarker] = {}
    order: list[str] = []
    for line in lines:
        parsed = parse_line(line, sex=sex)
        if not parsed:
            continue
        existing = by_name.get(parsed.test_name)
        if existing is None:
            by_name[parsed.test_name] = parsed
            order.append(parsed.test_name)
        elif existing.value is None and parsed.value is not None:
            by_name[parsed.test_name] = parsed
    return [by_name[name] for name in order]
