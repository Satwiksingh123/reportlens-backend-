"""Shared crop preprocessing for the recogniser.

TrOCR's processor resizes every crop to a square (384x384) ignoring aspect ratio. A wide
line crop (e.g. 220x14, aspect ~16) therefore gets stretched vertically ~25x and becomes
hard to read. Padding the short side with the background colour caps the aspect ratio, so
the square resize distorts the glyphs far less.

Applied identically in training (train_trocr) and inference (recognizer) so the model
never sees a distribution it wasn't trained on.
"""

from PIL import Image


def pad_to_aspect(image: Image.Image, max_aspect: float = 6.0, fill=(255, 255, 255)) -> Image.Image:
    """Pad the shorter side so width/height <= max_aspect, keeping the text centred."""
    img = image.convert("RGB")
    w, h = img.size
    if w == 0 or h == 0:
        return img
    if w / h <= max_aspect:
        return img
    target_h = int(round(w / max_aspect))
    canvas = Image.new("RGB", (w, target_h), fill)
    canvas.paste(img, (0, (target_h - h) // 2))
    return canvas
