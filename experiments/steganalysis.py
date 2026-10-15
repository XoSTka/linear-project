"""Can a simple statistic tell stego images from the originals? (task #19)

Idea: the plain scheme moves sigma_k to the centre of an interval, so sigma_k / delta mod 1 piles up at 0.5.
Statistic R = | mean exp(2*pi*i * sigma_k / delta) |  (length of the mean phase vector, 0 = uniform, 1 = all equal).
  * R_known : attacker knows (b, k, delta)                         -> best case for the attacker
  * R_blind : attacker scans delta in [8, 96] step 0.5 and keeps the maximum R
Compared on the 150 originals vs the same images with full-capacity random bits, plain and with a secret key.
Output: results/steganalysis.csv ; prints AUC (P(stego scores higher than original)).
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from svdmark import stego                                   # noqa: E402
from svdmark.data import list_images, load_gray, sample_images  # noqa: E402

B = 8
DELTAS = [16, 32]
KS = [0, 1]
SCAN = np.arange(8, 96.01, 0.5)
SAMPLE = sample_images(list_images(ROOT / "data" / "images"))


def sigma_k(A, k):
    return np.linalg.svd(stego._to_blocks(A, B), compute_uv=False)[:, k]


def R(s, delta):
    return float(np.abs(np.exp(2j * np.pi * s / delta).mean()))


def R_blind(s):
    return max(R(s, d) for d in SCAN)


def work(i):
    A = load_gray(SAMPLE["path"].iloc[i])
    bits = np.random.default_rng(i).integers(0, 2, stego.capacity(A.shape, B))
    rows = []
    for k in KS:
        s0 = sigma_k(A, k)
        for d in DELTAS:
            for mode, key in (("original", None), ("plain", None), ("keyed", "secret")):
                if mode == "original":
                    s = s0
                else:
                    s = sigma_k(stego.embed_bits(A, bits, d, B, k, key=key).image, k)
                rows.append(dict(image=SAMPLE["filename"].iloc[i], k=k, delta=d, mode=mode,
                                 R_known=R(s, d), R_blind=R_blind(s)))
    return rows


def auc(pos, neg):
    allv = np.concatenate([pos, neg])
    r = pd.Series(allv).rank().to_numpy()
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


if __name__ == "__main__":
    t0 = time.time()
    out = []
    with Pool(2) as pool:
        for n, rows in enumerate(pool.imap(work, range(len(SAMPLE))), 1):
            out += rows
            if n % 25 == 0:
                print(f"{n}/{len(SAMPLE)}  {time.time() - t0:.0f}s", flush=True)
    d = pd.DataFrame(out)
    d.to_csv(ROOT / "results" / "steganalysis.csv", index=False, float_format="%.5g")
    res = []
    for (k, delta), g in d.groupby(["k", "delta"]):
        o = g[g["mode"] == "original"]
        for mode in ("plain", "keyed"):
            s = g[g["mode"] == mode]
            res.append(dict(k=k, delta=delta, mode=mode,
                            R_known_orig=o["R_known"].mean(), R_known_stego=s["R_known"].mean(),
                            AUC_known=auc(s["R_known"].to_numpy(), o["R_known"].to_numpy()),
                            R_blind_orig=o["R_blind"].mean(), R_blind_stego=s["R_blind"].mean(),
                            AUC_blind=auc(s["R_blind"].to_numpy(), o["R_blind"].to_numpy())))
    pd.set_option("display.width", 200)
    print(pd.DataFrame(res).round(3).to_string(index=False))
    pd.DataFrame(res).to_csv(ROOT / "results" / "steganalysis_summary.csv", index=False, float_format="%.4f")
