"""PDF -> page image conversion for the OCR pipeline.

Real lab reports are usually uploaded as PDFs, not raw images. `pdf_to_images` renders
each page at a scan-quality resolution (300 dpi matches what we validated OCR accuracy
against) so the same recognisers used for image uploads work unchanged. Lazy-imports
PyMuPDF so importing ocr_engine stays cheap when PDF support isn't needed.
"""

from pathlib import Path

from PIL import Image


def pdf_to_images(path: str | Path, dpi: int = 300) -> list[Image.Image]:
    """Render every page of a PDF to a PIL image, in page order."""
    import fitz  # PyMuPDF; part of the `ocr` extra

    images: list[Image.Image] = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            images.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    return images
