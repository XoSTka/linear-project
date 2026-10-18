"""Whole pipeline on a real photo: hide Thai text, read it back."""

from pathlib import Path

import numpy as np

from svdmark.attacks import jpeg
from svdmark.data import load_gray
from svdmark.metrics import psnr
from svdmark.stego import embed_text, extract_text, text_capacity_bytes

ROOT = Path(__file__).resolve().parents[1]
A = load_gray(ROOT / "data/images/train/249061.jpg").astype(float)
print(
    "image matrix      :",
    A.shape,
    " capacity",
    text_capacity_bytes(A.shape),
    "bytes",
)

msg = "นัดเจอหน้าตึก ECC 5 โมง"
res = embed_text(A, msg, key="linear2026")  # b = 8, delta = 32, sigma_1
print(
    "PSNR              :",
    round(psnr(A, res.image), 2),
    "dB,",
    res.n_failed,
    "failed blocks",
)

for label, img, key in [
    ("right key        ", res.image, "linear2026"),
    ("wrong key        ", res.image, "linear2025"),
    ("right key, JPEG90", jpeg(res.image, 90), "linear2026"),
]:
    print(label, ":", extract_text(np.asarray(img, float), key=key))
