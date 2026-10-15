"""Pilot for watermarking: look at alpha on the VALIDATION split (30 images).

Writes results/pilot_watermark.csv (mean over images, one row per alpha x attack).
Columns: psnr_u8 (after rounding to 8-bit), ncc / ncc_c (raw and mean-removed NCC of the
extracted mark), ber (after threshold 0.5), and for the false-positive check the same
extraction run on the ORIGINAL image (never watermarked) and on a DIFFERENT image.
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from svdmark import attacks, watermark                     # noqa: E402
from svdmark.data import list_images, load_gray, sample_images  # noqa: E402
from svdmark.metrics import ber, ncc, psnr                 # noqa: E402

ALPHAS = [1, 2, 4, 8, 12, 16, 24, 32]
ATTACKS = [("none", None), ("noise", 2), ("noise", 4), ("jpeg", 90), ("jpeg", 75)]

val = sample_images(list_images(ROOT / "data" / "images"))
val = val[val["split"] == "val"].reset_index(drop=True)
imgs = [load_gray(p) for p in val["path"]]
k = min(imgs[0].shape)
W = np.random.default_rng(7).integers(0, 2, (k, k)).astype(float)


def ncc_c(a, b):
    return ncc(a - a.mean(), b - b.mean())


rows, t0 = [], time.time()
for alpha in ALPHAS:
    marked = [watermark.embed(A, W, alpha) for A in imgs]
    marked = [(np.clip(np.rint(Aw), 0, 255), key) for Aw, key in marked]
    base = {"alpha": alpha, "psnr_u8": np.mean([min(psnr(A, Au), 99.0) for A, (Au, _) in zip(imgs, marked)])}
    for name, lv in ATTACKS:
        tag = name if lv is None else f"{name}{lv}"
        ex = [watermark.extract(attacks.apply(name, Au, lv), key) for Au, key in marked]
        rows.append({**base, "attack": tag,
                     "ncc": np.mean([ncc(W, e) for e in ex]),
                     "ncc_c": np.mean([ncc_c(W, e) for e in ex]),
                     "ber": 100 * np.mean([ber(W, e > 0.5) for e in ex])})
    # false-positive checks: same key, but the image never carried the mark
    fp_orig = [watermark.extract(A, key) for A, (_, key) in zip(imgs, marked)]
    fp_other = [watermark.extract(imgs[(i + 1) % len(imgs)], key) for i, (_, key) in enumerate(marked)]
    rows.append({**base, "attack": "FP_original", "ncc": np.mean([ncc(W, e) for e in fp_orig]),
                 "ncc_c": np.mean([ncc_c(W, e) for e in fp_orig]), "ber": 100 * np.mean([ber(W, e > 0.5) for e in fp_orig])})
    rows.append({**base, "attack": "FP_other", "ncc": np.mean([ncc(W, e) for e in fp_other]),
                 "ncc_c": np.mean([ncc_c(W, e) for e in fp_other]), "ber": 100 * np.mean([ber(W, e > 0.5) for e in fp_other])})
    print(f"alpha={alpha} done {time.time() - t0:.0f}s", flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results" / "pilot_watermark.csv", index=False, float_format="%.4f")
