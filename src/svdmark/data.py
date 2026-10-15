"""Dataset helpers: load an image as a grayscale float matrix, pick the experiment set.

Pipeline (same as notebooks 00-02): RGB -> grayscale (ITU-R 601 luma, 0.299R+0.587G+0.114B)
-> centre-crop so both sides are multiples of `multiple` (default 16, so block sizes
2, 4, 8 and 16 all tile the image exactly).  BSDS500 images (481x321 / 321x481)
become 480x320 / 320x480.  No resizing, so pixel values are never recomputed.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

SEED = 42
N_SAMPLE = 150


def crop_to_multiple(a: np.ndarray, multiple: int = 16) -> np.ndarray:
    """Centre-crop a 2-D array so that both sides are multiples of `multiple`."""
    h, w = a.shape
    nh, nw = h - h % multiple, w - w % multiple
    if nh == 0 or nw == 0:
        raise ValueError(f"image {w}x{h} is smaller than one {multiple}x{multiple} block")
    top, left = (h - nh) // 2, (w - nw) // 2
    return a[top:top + nh, left:left + nw]


def to_gray(img: Image.Image) -> np.ndarray:
    """PIL image (any mode, incl. RGBA/palette) -> float64 grayscale matrix in 0..255."""
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))   # flatten transparency on white
        img = Image.alpha_composite(bg, img)
    return np.asarray(img.convert("L"), dtype=np.float64)


def load_gray(path_or_image, multiple: int = 16) -> np.ndarray:
    """Load a file path or PIL image as a cropped grayscale float matrix."""
    img = path_or_image if isinstance(path_or_image, Image.Image) else Image.open(path_or_image)
    return crop_to_multiple(to_gray(img), multiple)


def list_images(root: str | Path) -> pd.DataFrame:
    """All .jpg files under root/<split>/, sorted so sampling is reproducible."""
    root = Path(root)
    rows = [{"split": p.parent.name, "filename": p.name, "path": str(p)}
            for p in sorted(root.glob("*/*.jpg"))]
    return pd.DataFrame(rows)


def sample_images(df: pd.DataFrame, n: int = N_SAMPLE, seed: int = SEED) -> pd.DataFrame:
    """Random n images with a fixed seed (same list every run)."""
    idx = np.random.default_rng(seed).choice(len(df), size=n, replace=False)
    return df.iloc[np.sort(idx)].reset_index(drop=True)
