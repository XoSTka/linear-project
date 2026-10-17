"""Pilot for steganography: choose b, delta and the sigma index k on the PILOT set only.

The pilot set is the 100 BSDS500 `val` images; it shares no image with the 400-image evaluation set
used for every reported number, so the parameters are never tuned on the images they are judged on.
Writes results/pilot_stego.csv  (one row per config, mean over the pilot images).
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from svdmark import attacks, stego
from svdmark.data import list_images, load_gray, pilot_set
from svdmark.metrics import ber, psnr

ROOT = Path(__file__).resolve().parents[1]

BLOCKS = [4, 8, 16]
DELTAS = [8, 12, 16, 24, 32, 48, 64]
KS = [0, 1, 2, 3]
ATTACKS = [("none", None), ("noise", 2), ("noise", 4), ("jpeg", 90), ("jpeg", 75)]
PILOT = pilot_set(list_images(ROOT / "data" / "images"))


def work(i):
    A = load_gray(PILOT["path"].iloc[i])
    rows = []
    for b in BLOCKS:
        bits = np.random.default_rng([2024, i, b]).integers(0, 2, stego.capacity(A.shape, b))
        for d in DELTAS:
            for k in KS:
                r = stego.embed_bits(A, bits, d, b, k)
                rec = {"b": b, "delta": d, "k": k, "psnr": psnr(A, r.image), "failed_pct": 100 * r.n_failed / r.n_bits}
                for name, lv in ATTACKS:
                    tag = attacks.label(name, lv)
                    got = stego.extract_bits(attacks.apply(name, r.image, lv, seed=i), len(bits), d, b, k)
                    rec[f"ber_{tag}"] = 100 * ber(bits, got)
                rows.append(rec)
    return rows


if __name__ == "__main__":
    t0 = time.time()
    out = []
    with Pool(2) as pool:
        for n, rows in enumerate(pool.imap(work, range(len(PILOT))), 1):
            out += rows
            if n % 10 == 0:
                print(f"{n}/{len(PILOT)} images  {time.time() - t0:.0f}s", flush=True)
    d = pd.DataFrame(out)
    m = d.groupby(["b", "delta", "k"]).mean().reset_index()
    m["pass40"] = d.groupby(["b", "delta", "k"])["psnr"].apply(lambda x: (x >= 40).mean()).to_numpy()
    m.to_csv(ROOT / "results" / "pilot_stego.csv", index=False, float_format="%.4f")
    print(len(PILOT), "pilot images,", len(m), "configs")
