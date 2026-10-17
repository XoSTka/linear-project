"""Attacks applied to an 8-bit grayscale image (float matrix with values 0..255).

Every attack returns an integer-valued float matrix of the SAME shape, as if the
attacked picture had been saved as an 8-bit image and loaded again.  The levels
are fixed here, before any results are seen, and shared by watermarking and
steganography so the two parts are compared under identical conditions.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter

# name -> levels (weakest first).  "none" is always run as the reference.
LEVELS = {
    "noise": [1, 2, 4, 8],  # Gaussian noise, std in grey levels (PSNR ~48/42/36/30 dB)
    "jpeg": [95, 90, 75, 50],  # JPEG quality factor
    "crop": [0.05, 0.10, 0.25],  # fraction of the image area removed (set to 0), centred
}


def _to_uint8_like(a: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(a), 0, 255)


def gaussian_noise(A: np.ndarray, std: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return _to_uint8_like(np.asarray(A, dtype=float) + rng.normal(0.0, std, np.shape(A)))


def jpeg(A: np.ndarray, quality: int) -> np.ndarray:
    buf = io.BytesIO()
    Image.fromarray(_to_uint8_like(A).astype(np.uint8), mode="L").save(buf, format="JPEG", quality=int(quality))
    buf.seek(0)
    return np.asarray(Image.open(buf).convert("L"), dtype=float)


def crop_out(A: np.ndarray, fraction: float) -> np.ndarray:
    """Remove a centred rectangle holding `fraction` of the area (pixels set to 0).

    The rectangle keeps the image's aspect ratio, so its sides are sqrt(fraction)
    of the image sides.  The image size is unchanged so extraction can still align.
    """
    A = _to_uint8_like(A).copy()
    h, w = A.shape
    s = np.sqrt(fraction)
    ch, cw = int(round(h * s)), int(round(w * s))
    top, left = (h - ch) // 2, (w - cw) // 2
    A[top : top + ch, left : left + cw] = 0.0
    return A


# Extra attacks (used by experiments/robustness_extra.py and the demo; NOT part of the main grid above, so the
# main results stay comparable).  They change the geometry or smooth the image, which SVD-based schemes dislike.
EXTRA_LEVELS = {
    "resize": [0.75, 0.5],  # shrink to this fraction of the size, then enlarge back (like a re-upload)
    "blur": [0.5, 1.0],  # Gaussian blur radius in pixels
    "median": [3],  # median filter window (3 x 3)
    "rotate": [0.5, 1.0],  # rotate by this many degrees (same canvas size)
}


def _pil(A):
    return Image.fromarray(_to_uint8_like(A).astype(np.uint8), mode="L")


def resize_back(A: np.ndarray, factor: float) -> np.ndarray:
    im = _pil(A)
    w, h = im.size
    small = im.resize((max(1, round(w * factor)), max(1, round(h * factor))), Image.LANCZOS)
    return np.asarray(small.resize((w, h), Image.BICUBIC), dtype=float)


def blur(A: np.ndarray, radius: float) -> np.ndarray:
    return np.asarray(_pil(A).filter(ImageFilter.GaussianBlur(radius)), dtype=float)


def median(A: np.ndarray, size: int) -> np.ndarray:
    return np.asarray(_pil(A).filter(ImageFilter.MedianFilter(int(size))), dtype=float)


def rotate(A: np.ndarray, degrees: float) -> np.ndarray:
    im = _pil(A)
    fill = int(np.median(np.asarray(im)))
    return np.asarray(im.rotate(degrees, resample=Image.BICUBIC, expand=False, fillcolor=fill), dtype=float)


def apply(name: str, A: np.ndarray, level=None, seed: int = 0) -> np.ndarray:
    if name == "none":
        return _to_uint8_like(A)
    if name == "noise":
        return gaussian_noise(A, level, seed)
    if name == "jpeg":
        return jpeg(A, level)
    if name == "crop":
        return crop_out(A, level)
    if name == "resize":
        return resize_back(A, level)
    if name == "blur":
        return blur(A, level)
    if name == "median":
        return median(A, level)
    if name == "rotate":
        return rotate(A, level)
    raise ValueError(f"unknown attack {name!r}")


def label(name: str, level=None) -> str:
    """Short name used in the result tables: ("jpeg", 75) -> "jpeg75", ("none", None) -> "none"."""
    return name if level is None else f"{name}{level}"


def all_attacks():
    """Yield (name, level) for the reference run and every defined level."""
    yield "none", None
    for name, levels in LEVELS.items():
        for lv in levels:
            yield name, lv


def extra_attacks():
    """Yield (name, level) for every extra attack."""
    for name, levels in EXTRA_LEVELS.items():
        for lv in levels:
            yield name, lv
