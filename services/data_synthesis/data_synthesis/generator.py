"""Synthetic lab-report generator.

Produces (image, ground_truth) pairs for OCR training and parser evaluation:
  - a rendered report image (varied layout / fonts / noise),
  - the exact text and per-line bounding boxes (OCR supervision),
  - the structured biomarkers with known status (parser supervision).

Because it reuses the same reference table as the parser, the "true" status of every
sampled value is known, which lets us measure parser accuracy automatically.
"""

import random
from dataclasses import dataclass, field

from data_synthesis.ranges import BiomarkerRef, panel_biomarkers, panel_names

FIRST_NAMES = ["Aarav", "Diya", "Kabir", "Meera", "Rohan", "Sara", "Vivaan", "Anaya"]
LAST_NAMES = ["Sharma", "Patel", "Reddy", "Khan", "Nair", "Gupta", "Iyer", "Bose"]
LABS = ["MediCore Diagnostics", "PathCare Labs", "LifeLine Diagnostics", "Apollo Path"]


@dataclass
class BiomarkerRow:
    panel: str
    test_name: str
    value: str
    unit: str | None
    reference_range: str | None
    status: str  # ground-truth Low/Normal/High


@dataclass
class SyntheticReport:
    panel: str
    patient_name: str
    patient_age: int
    patient_sex: str
    lab_name: str
    rows: list[BiomarkerRow]
    text_lines: list[str] = field(default_factory=list)

    def to_ground_truth(self) -> dict:
        return {
            "panel": self.panel,
            "patient": {
                "name": self.patient_name,
                "age": self.patient_age,
                "sex": self.patient_sex,
            },
            "lab": self.lab_name,
            "biomarkers": [
                {
                    "test_name": r.test_name,
                    "value": r.value,
                    "unit": r.unit,
                    "reference_range": r.reference_range,
                    "status": r.status,
                }
                for r in self.rows
            ],
        }


def _fmt(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def _fmt_range(ref: BiomarkerRef) -> str | None:
    if ref.low is not None and ref.high is not None:
        return f"{_fmt(ref.low)}-{_fmt(ref.high)}"
    if ref.high is not None:
        return f"<{_fmt(ref.high)}"
    if ref.low is not None:
        return f">{_fmt(ref.low)}"
    return None


def _sample_value(ref: BiomarkerRef, target_status: str, rng: random.Random) -> tuple[float, str]:
    """Sample a numeric value whose true status matches target_status.

    Falls back to Normal when the reference interval can't express the target
    (e.g. a one-sided range has no way to be 'Low')."""
    low, high = ref.low, ref.high

    def _round(v: float) -> float:
        # integer-ish quantities stay whole; small quantities keep one decimal
        if high is not None and high >= 1000:
            return float(int(v))
        return round(v, 1)

    if target_status == "High" and high is not None:
        return _round(rng.uniform(high * 1.05, high * 1.4)), "High"
    if target_status == "Low" and low is not None:
        lo = max(0.0, low * 0.6)
        return _round(rng.uniform(lo, low * 0.95)), "Low"

    # Normal (or fallback): sample inside the interval
    if low is not None and high is not None:
        return _round(rng.uniform(low, high)), "Normal"
    if high is not None:
        return _round(rng.uniform(high * 0.4, high * 0.95)), "Normal"
    if low is not None:
        return _round(rng.uniform(low * 1.05, low * 1.6)), "Normal"
    return 0.0, "Normal"


def generate_report(
    panel: str | None = None,
    sex: str | None = None,
    abnormal_rate: float = 0.3,
    seed: int | None = None,
) -> SyntheticReport:
    rng = random.Random(seed)
    panel = panel or rng.choice(panel_names())
    sex = sex or rng.choice(["M", "F"])
    name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    age = rng.randint(18, 80)
    lab = rng.choice(LABS)

    rows: list[BiomarkerRow] = []
    for ref in panel_biomarkers(panel, sex):
        if rng.random() < abnormal_rate:
            target = rng.choice(["Low", "High"])
        else:
            target = "Normal"
        value, actual_status = _sample_value(ref, target, rng)
        rows.append(
            BiomarkerRow(
                panel=ref.panel,
                test_name=ref.canonical,
                value=_fmt(value),
                unit=ref.unit,
                reference_range=_fmt_range(ref),
                status=actual_status,
            )
        )

    report = SyntheticReport(
        panel=panel,
        patient_name=name,
        patient_age=age,
        patient_sex=sex,
        lab_name=lab,
        rows=rows,
    )
    report.text_lines = _build_text_lines(report)
    return report


def _build_text_lines(report: SyntheticReport) -> list[str]:
    lines = [
        report.lab_name,
        "LABORATORY REPORT",
        f"Patient: {report.patient_name}    Age/Sex: {report.patient_age}/{report.patient_sex}",
        f"Panel: {report.panel}",
        "",
        f"{'Test':28}{'Result':10}{'Unit':16}{'Reference Range':16}",
    ]
    for r in report.rows:
        lines.append(
            f"{r.test_name:28}{r.value:10}{(r.unit or ''):16}{(r.reference_range or ''):16}"
        )
    return lines


def render_report(report: SyntheticReport, add_noise: bool = True, seed: int | None = None):
    """Render the report to a PIL image plus per-line bounding boxes.

    Returns (PIL.Image, list[dict]) where each dict is {"text", "box": (x0,y0,x1,y1)}.
    """
    # lazy import keeps PIL cost off code paths that only need text/ground truth
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    rng = random.Random(seed)
    width, height = 1000, 120 + 26 * len(report.text_lines)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", 16)
    except OSError:
        font = ImageFont.load_default()

    boxes = []
    x0, y = 40, 40
    for i, line in enumerate(report.text_lines):
        if not line:
            y += 26
            continue
        # header emphasis via a heavier draw (double-strike) for the first two lines
        draw.text((x0, y), line, fill="black", font=font)
        if i < 2:
            draw.text((x0 + 1, y), line, fill="black", font=font)
        bbox = draw.textbbox((x0, y), line, font=font)
        boxes.append({"text": line, "box": bbox})
        y += 26

    if add_noise:
        img = _apply_scan_noise(img, rng, Image, ImageFilter)

    return img, boxes


def _apply_scan_noise(img, rng, Image, ImageFilter):
    """Light, realistic scan degradation: rotation, blur, speckle."""
    angle = rng.uniform(-1.5, 1.5)
    img = img.rotate(angle, expand=False, fillcolor="white")
    if rng.random() < 0.5:
        img = img.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.3, 0.8)))
    # Speckle: light grey dust, kept lighter than typical OCR ink thresholds and sparse, so
    # it reads as realistic scan noise without masquerading as text and inflating line
    # bounding boxes to full page width.
    px = img.load()
    w, h = img.size
    for _ in range(int(w * h * 0.0008)):
        x, y = rng.randint(0, w - 1), rng.randint(0, h - 1)
        shade = rng.randint(170, 215)
        px[x, y] = (shade, shade, shade)
    return img
