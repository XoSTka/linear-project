"""Attacks applied to an 8-bit grayscale image (float matrix with values 0..255).

Every attack returns an integer-valued float matrix of the SAME shape, as if the
attacked picture had been saved as an 8-bit image and loaded again.  The levels
are fixed here, before any results are seen, and shared by watermarking and
steganography so the two parts are compared under identical conditions.
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image

# name -> levels (weakest first).  "none" is always run as the reference.
LEVELS = {
    "noise": [1, 2, 4, 8],          # Gaussian noise, std in grey levels (PSNR ~48/42/36/30 dB)
    "jpeg": [95, 90, 75, 50],       # JPEG quality factor
    "crop": [0.05, 0.10, 0.25],     # fraction of the image area removed (set to 0), centred
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
    A[top:top + ch, left:left + cw] = 0.0
    return A


def apply(name: str, A: np.ndarray, level=None, seed: int = 0) -> np.ndarray:
    if name == "none":
        return _to_uint8_like(A)
    if name == "noise":
        return gaussian_noise(A, level, seed)
    if name == "jpeg":
        return jpeg(A, level)
    if name == "crop":
        return crop_out(A, level)
    raise ValueError(f"unknown attack {name!r}")


def all_attacks():
    """Yield (name, level) for the reference run and every defined level."""
    yield "none", None
    for name, levels in LEVELS.items():
        for lv in levels:
            yield name, lv
