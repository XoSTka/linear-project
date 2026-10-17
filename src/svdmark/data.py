"""Dataset helpers: load an image as a grayscale float matrix, pick the experiment set.

Pipeline (same as notebooks 00-02): RGB -> grayscale (ITU-R 601 luma, 0.299R+0.587G+0.114B)
-> centre-crop so both sides are multiples of `multiple` (default 16, so block sizes
2, 4, 8 and 16 all tile the image exactly).  BSDS500 images (481x321 / 321x481)
become 480x320 / 320x480.  No resizing, so pixel values are never recomputed.

Which images are used for what (BSDS500 ships 200 train / 100 val / 200 test):
  * pilot_set   the 100 `val` images  -> used ONLY to choose parameters (b, delta, k, alpha)
  * eval_set    the 400 `train` + `test` images -> every reported number; never used for tuning
The original BSDS500 split names are kept only as a convenient fixed partition: nothing is trained.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

PILOT_SPLITS = ("val",)
EVAL_SPLITS = ("train", "test")


def crop_to_multiple(a: np.ndarray, multiple: int = 16) -> np.ndarray:
    """Centre-crop a 2-D array so that both sides are multiples of `multiple`."""
    h, w = a.shape
    nh, nw = h - h % multiple, w - w % multiple
    if nh == 0 or nw == 0:
        raise ValueError(f"image {w}x{h} is smaller than one {multiple}x{multiple} block")
    top, left = (h - nh) // 2, (w - nw) // 2
    return a[top : top + nh, left : left + nw]


def to_gray(img: Image.Image) -> np.ndarray:
    """PIL image (any mode, incl. RGBA/palette) -> float64 grayscale matrix in 0..255."""
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))  # flatten transparency on white
        img = Image.alpha_composite(bg, img)
    return np.asarray(img.convert("L"), dtype=np.float64)


def load_gray(path_or_image, multiple: int = 16) -> np.ndarray:
    """Load a file path or PIL image as a cropped grayscale float matrix."""
    img = path_or_image if isinstance(path_or_image, Image.Image) else Image.open(path_or_image)
    return crop_to_multiple(to_gray(img), multiple)


def list_images(root: str | Path) -> pd.DataFrame:
    """All .jpg files under root/<split>/, sorted by path so every run sees them in the same order."""
    root = Path(root)
    rows = [{"split": p.parent.name, "filename": p.name, "path": str(p)} for p in sorted(root.glob("*/*.jpg"))]
    return pd.DataFrame(rows)


def pilot_set(df: pd.DataFrame) -> pd.DataFrame:
    """Images used to choose parameters (the `val` split, 100 images of BSDS500)."""
    return df[df["split"].isin(PILOT_SPLITS)].reset_index(drop=True)


def eval_set(df: pd.DataFrame) -> pd.DataFrame:
    """Images every reported number comes from (`train` + `test`, 400 images); disjoint from pilot_set."""
    return df[df["split"].isin(EVAL_SPLITS)].reset_index(drop=True)
