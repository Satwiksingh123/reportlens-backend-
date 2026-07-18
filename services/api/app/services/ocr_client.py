"""Thin client that will call the ocr_engine service.

For now returns a stub so the pipeline is testable. Real implementation will invoke
the fine-tuned docTR/PaddleOCR model (see services/ocr_engine).
"""


def extract_text(path: str, content_type: str) -> str:
    # TODO: call services/ocr_engine inference. Placeholder text below.
    return (
        "Complete Blood Count (CBC)\n"
        "Hemoglobin 11.2 g/dL 13.0-17.0\n"
        "WBC 11500 /uL 4000-11000\n"
        "Platelets 210000 /uL 150000-410000\n"
    )
