"""Pilot for steganography: choose b, delta and the sigma index k on the VALIDATION split.

Selection happens here, on the 30 validation images of the 150-image sample, so the
full run can report on all 150 without having tuned on them.
Writes results/pilot_stego.csv  (one row per config x attack, mean over images).
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from svdmark import attacks, stego                      # noqa: E402
from svdmark.data import list_images, load_gray, sample_images  # noqa: E402
from svdmark.metrics import ber, psnr                   # noqa: E402

BLOCKS = [4, 8, 16]
DELTAS = [8, 12, 16, 24, 32, 48, 64]
KS = [0, 1, 2, 3]
ATTACKS = [("none", None), ("noise", 2), ("noise", 4), ("jpeg", 90), ("jpeg", 75)]

df = sample_images(list_images(ROOT / "data" / "images"))
val = df[df["split"] == "val"].reset_index(drop=True)
imgs = [load_gray(p) for p in val["path"]]
rng = np.random.default_rng(2024)
t0 = time.time()
rows = []
for b in BLOCKS:
    bits_all = [rng.integers(0, 2, stego.capacity(A.shape, b)) for A in imgs]
    for d in DELTAS:
        for k in KS:
            res = [stego.embed_bits(A, bits, d, b, k) for A, bits in zip(imgs, bits_all)]
            rec = {"b": b, "delta": d, "k": k,
                   "psnr": np.mean([psnr(A, r.image) for A, r in zip(imgs, res)]),
                   "failed_pct": 100 * np.mean([r.n_failed / r.n_bits for r in res])}
            for name, lv in ATTACKS:
                tag = name if lv is None else f"{name}{lv}"
                rec[f"ber_{tag}"] = 100 * np.mean([
                    ber(bits, stego.extract_bits(attacks.apply(name, r.image, lv), len(bits), d, b, k))
                    for bits, r in zip(bits_all, res)])
            rows.append(rec)
    print(f"b={b} done  {time.time() - t0:.0f}s", flush=True)
out = pd.DataFrame(rows)
out.to_csv(ROOT / "results" / "pilot_stego.csv", index=False, float_format="%.4f")
print(len(val), "validation images,", len(out), "configs")
