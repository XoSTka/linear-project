"""Does a whole MESSAGE survive?  Error correction (Hamming 7,4) on/off, main attacks plus extra attacks.

The main experiment (full_stego.py) measures the bit error rate of random bits.  A real message needs EVERY bit
right (one wrong bit -> CRC fails -> 'damaged').  Here we hide a real 34-byte Thai message and count how often it
comes back exactly ('ok'), with and without error correction, on 100 evaluation images (every 4th one).
The same images also test the watermark (alpha 8 and 16, random 320x320 mark) under the extra attacks.

Outputs: results/robustness_extra.csv (stego, one row per image x setting x attack)
         results/robustness_extra_wm.csv (watermark, one row per image x alpha x attack)
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from svdmark import attacks, stego, watermark
from svdmark.data import eval_set, list_images, load_gray
from svdmark.metrics import auc, ncc

ROOT = Path(__file__).resolve().parents[1]

TEXT = "พบกัน 15:00 ตึก 12"  # 34 bytes: fits every setting, also b = 16 with error correction (38 bytes)
KEY = "kmitl-2026"
SETTINGS = [(16, 64.0), (8, 32.0), (4, 16.0)]
ATT = list(attacks.all_attacks()) + [("jpeg", 60)] + list(attacks.extra_attacks())
IMAGES = eval_set(list_images(ROOT / "data" / "images")).iloc[::4].reset_index(drop=True)
ALPHAS = [8, 16]


def work(i):
    A = load_gray(IMAGES["path"].iloc[i])
    rows, wrows = [], []
    for b, d in SETTINGS:
        for use_ecc in (False, True):
            r = stego.embed_text(A, TEXT, d, b, key=KEY, ecc=use_ecc)
            for n, lv in ATT:
                B = attacks.apply(n, r.image, lv, seed=i)
                text, status, fixed = stego.extract_text(B, d, b, key=KEY, ecc=use_ecc, details=True)
                rows.append(
                    dict(
                        image=IMAGES["filename"].iloc[i],
                        b=b,
                        delta=d,
                        ecc=use_ecc,
                        attack=attacks.label(n, lv),
                        ok=status == "ok",
                        status=status,
                        corrected=fixed,
                    )
                )
    k = min(A.shape)
    W = np.random.default_rng(7).integers(0, 2, (k, k)).astype(float)
    for alpha in ALPHAS:
        Aw, key = watermark.embed(A, W, alpha)
        Au = np.clip(np.rint(Aw), 0, 255)
        for n, lv in [("none", None)] + list(attacks.extra_attacks()):
            s_m = watermark.singular_values(attacks.apply(n, Au, lv, seed=i))
            s_f = watermark.singular_values(attacks.apply(n, A, lv, seed=i))
            wrows.append(
                dict(
                    image=IMAGES["filename"].iloc[i],
                    alpha=alpha,
                    attack=attacks.label(n, lv),
                    ncc=ncc(W, watermark.extract_from_sigma(s_m, key)),
                    fp_ncc=ncc(W, watermark.extract_from_sigma(s_f, key)),
                    shift=watermark.shift_from_sigma(s_m, key),
                    fp_shift=watermark.shift_from_sigma(s_f, key),
                )
            )
    return rows, wrows


if __name__ == "__main__":
    t0 = time.time()
    rows, wrows = [], []
    with Pool(2) as pool:
        for n, (r, w) in enumerate(pool.imap(work, range(len(IMAGES))), 1):
            rows += r
            wrows += w
            if n % 20 == 0:
                print(f"{n}/{len(IMAGES)} images  {time.time() - t0:.0f}s", flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(ROOT / "results" / "robustness_extra.csv", index=False)
    w = pd.DataFrame(wrows)
    w.to_csv(ROOT / "results" / "robustness_extra_wm.csv", index=False, float_format="%.5g")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    order = [attacks.label(n, lv) for n, lv in ATT]
    t = d.pivot_table(index="attack", columns=["b", "ecc"], values="ok", aggfunc="mean").reindex(order) * 100
    print("\nmessage comes back exactly (% of images)\n", t.round(0).to_string())
    summ = []
    for (a, att), g in w.groupby(["alpha", "attack"], sort=False):
        summ.append(
            dict(
                alpha=a,
                attack=att,
                ncc=g.ncc.mean(),
                fp_ncc=g.fp_ncc.mean(),
                shift=g["shift"].mean(),
                fp_shift=g.fp_shift.mean(),
                auc_shift=auc(g["shift"].to_numpy(), g.fp_shift.to_numpy()),
                auc_ncc=auc(g.ncc.to_numpy(), g.fp_ncc.to_numpy()),
            )
        )
    s = pd.DataFrame(summ)
    s.to_csv(ROOT / "results" / "robustness_extra_wm_summary.csv", index=False, float_format="%.4f")
    print("\nwatermark under extra attacks\n", s.round(3).to_string(index=False))
