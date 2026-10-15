"""Full watermark experiment on the 150-image sample (task #8, also data for #14).

For every image, alpha and attack (`attacks.all_attacks`) it records
  * quality of the marked image (PSNR after 8-bit rounding),
  * NCC / mean-removed NCC / BER of the extracted mark,           [marked, attacked]
  * the same extraction on the SAME image never marked,            [fp_*]  false positive
  * NCC of the extraction on a DIFFERENT image never marked,       [other_*]
  * shift_score (singular-value shift test) for all three.
Output: results/watermark_full.csv (one row per image x alpha x attack).
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
from svdmark import attacks, watermark                      # noqa: E402
from svdmark.data import list_images, load_gray, sample_images  # noqa: E402
from svdmark.metrics import ber, ncc, psnr                  # noqa: E402

ALPHAS = [2, 4, 8, 12, 16, 24]
SEED_W = 7
ATT = list(attacks.all_attacks())
SAMPLE = sample_images(list_images(ROOT / "data" / "images"))


def tag(name, lv):
    return name if lv is None else f"{name}{lv}"


def ncc_c(a, b):
    return ncc(a - a.mean(), b - b.mean())


def sigmas_unmarked(i):
    """sigma of image i after every attack, never marked."""
    A = load_gray(SAMPLE["path"].iloc[i])
    return {tag(n, lv): watermark.singular_values(attacks.apply(n, A, lv, seed=i)) for n, lv in ATT}


def work(i):
    A = load_gray(SAMPLE["path"].iloc[i])
    k = min(A.shape)
    W = np.random.default_rng(SEED_W).integers(0, 2, (k, k)).astype(float)
    own = sigmas_unmarked(i)
    other = sigmas_unmarked((i + 37) % len(SAMPLE))
    rows = []
    for alpha in ALPHAS:
        Aw, key = watermark.embed(A, W, alpha)
        Au = np.clip(np.rint(Aw), 0, 255)
        p = psnr(A, Au)
        for n, lv in ATT:
            t = tag(n, lv)
            s_m = watermark.singular_values(attacks.apply(n, Au, lv, seed=i))
            W_m = watermark.extract_from_sigma(s_m, key)
            W_f = watermark.extract_from_sigma(own[t], key)
            W_o = watermark.extract_from_sigma(other[t], key)
            rows.append(dict(image=SAMPLE["filename"].iloc[i], split=SAMPLE["split"].iloc[i], alpha=alpha, attack=t,
                             psnr_u8=min(p, 99.0), identical=bool(np.isinf(p)),
                             ncc=ncc(W, W_m), ncc_c=ncc_c(W, W_m), ber=ber(W, W_m > 0.5),
                             shift=watermark.shift_from_sigma(s_m, key),
                             fp_ncc=ncc(W, W_f), fp_ncc_c=ncc_c(W, W_f), fp_ber=ber(W, W_f > 0.5),
                             fp_shift=watermark.shift_from_sigma(own[t], key),
                             other_ncc=ncc(W, W_o), other_shift=watermark.shift_from_sigma(other[t], key)))
    return rows


if __name__ == "__main__":
    t0 = time.time()
    out = []
    with Pool(2) as pool:
        for n, rows in enumerate(pool.imap(work, range(len(SAMPLE))), 1):
            out += rows
            if n % 10 == 0:
                print(f"{n}/{len(SAMPLE)} images  {time.time() - t0:.0f}s", flush=True)
    pd.DataFrame(out).to_csv(ROOT / "results" / "watermark_full.csv", index=False, float_format="%.5g")
    print("done", len(out), "rows")
