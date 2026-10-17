"""Full steganography experiment on the evaluation set (400 train+test images, never used for tuning).

Grid fixed by the pilot (results/pilot_decisions.md): k in {0, 1}; b in {4, 8, 16};
delta = c * b with c in {2, 3, 4, 6, 8}; every attack in `attacks.all_attacks`.
Each image is filled to capacity with random bits (seeded per image and block size).
Output: results/stego_full.csv (one row per image x config x attack).
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
from svdmark.data import eval_set, list_images, load_gray
from svdmark.metrics import ber, psnr

ROOT = Path(__file__).resolve().parents[1]

KS = [0, 1]
BLOCKS = [4, 8, 16]
CS = [2, 3, 4, 6, 8]
ATT = list(attacks.all_attacks())
SAMPLE = eval_set(list_images(ROOT / "data" / "images"))


def work(i):
    A = load_gray(SAMPLE["path"].iloc[i])
    rows = []
    for b in BLOCKS:
        bits = np.random.default_rng(1000 * i + b).integers(0, 2, stego.capacity(A.shape, b))
        for c in CS:
            d = c * b
            for k in KS:
                r = stego.embed_bits(A, bits, d, b, k)
                base = dict(
                    image=SAMPLE["filename"].iloc[i],
                    split=SAMPLE["split"].iloc[i],
                    k=k,
                    b=b,
                    delta=d,
                    c=c,
                    bits=len(bits),
                    psnr=psnr(A, r.image),
                    failed_pct=100 * r.n_failed / r.n_bits,
                )
                for n, lv in ATT:
                    got = stego.extract_bits(attacks.apply(n, r.image, lv, seed=i), len(bits), d, b, k)
                    rows.append({**base, "attack": attacks.label(n, lv), "ber": 100 * ber(bits, got)})
    return rows


if __name__ == "__main__":
    t0 = time.time()
    out = []
    with Pool(2) as pool:
        for n, rows in enumerate(pool.imap(work, range(len(SAMPLE))), 1):
            out += rows
            if n % 5 == 0:
                print(f"{n}/{len(SAMPLE)} images  {time.time() - t0:.0f}s", flush=True)
    pd.DataFrame(out).to_csv(ROOT / "results" / "stego_full.csv", index=False, float_format="%.5g")
    print("done", len(out), "rows")
