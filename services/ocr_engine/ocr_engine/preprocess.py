"""Shared crop preprocessing for the recogniser.

TrOCR's processor resizes every crop to a square (384x384) ignoring aspect ratio. A wide
line crop (e.g. 220x14, aspect ~16) therefore gets stretched vertically ~25x and becomes
hard to read. Padding the short side with the background colour caps the aspect ratio, so
the square resize distorts the glyphs far less.

Applied identically in training (train_trocr) and inference (recognizer) so the model
never sees a distribution it wasn't trained on.
"""

from PIL import Image


def letterbox_square(image: Image.Image, size: int = 384, fill=(255, 255, 255)) -> Image.Image:
    """Resize a crop into a centred square, preserving aspect ratio (letterboxing).

    TrOCR's processor resizes every input to a 384x384 square with a plain (non
    aspect-preserving) resize, so a wide word crop gets stretched vertically and the glyphs
    distort. Pre-fitting the crop into a square with white padding means that resize becomes
    a no-op and the text keeps its true shape. Applied identically in training and
    inference so the model never sees a distribution it wasn't trained on.
    """
    img = image.convert("RGB")
    w, h = img.size
    if w == 0 or h == 0:
        return Image.new("RGB", (size, size), fill)
    scale = size / max(w, h)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    resized = img.resize((nw, nh), Image.BILINEAR)
    canvas = Image.new("RGB", (size, size), fill)
    canvas.paste(resized, ((size - nw) // 2, (size - nh) // 2))
    return canvas
