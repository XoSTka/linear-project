"""Can a trained detector (machine learning) tell our stego / watermarked images from normal ones?

The earlier test (steganalysis.py) used one hand-made statistic.  Here a classifier LEARNS from examples:
  * train: the 100 pilot images, each as a normal image (label 0) and as a modified image (label 1)
  * test : the 400 evaluation images (never seen in training), same two versions
Features (11 numbers per image, all computed from pixels only -- no key, no parameters needed):
  * blockiness at grid 4, 8, 16: how much larger the brightness jumps are ACROSS block borders than inside blocks.
    Why it should work: changing sigma_1 of a block adds d * u1 v1^T, and for a smooth block u1, v1 are nearly
    flat vectors, so the whole block gets almost the same brightness shift -> a small step at every block border.
  * phase concentration R of sigma_1 / delta, maximised over delta (the statistic of steganalysis.py), b = 8
  * histogram of horizontal pixel differences |d| = 0, 1, 2, 3, 4-7, >= 8 (share of pixels)
Classifier: logistic regression (written here with numpy; features standardised on the training set).
Output: results/ml_steganalysis.csv (AUC and accuracy on the evaluation images, per condition)
        results/ml_features.csv     (all feature values, for inspection)
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from svdmark import stego, watermark
from svdmark.data import eval_set, list_images, load_gray, pilot_set
from svdmark.metrics import auc

ROOT = Path(__file__).resolve().parents[1]

ALL = list_images(ROOT / "data" / "images")
IMGS = pd.concat([pilot_set(ALL).assign(role="train"), eval_set(ALL).assign(role="test")]).reset_index(drop=True)
SCAN = np.arange(8, 96.01, 0.5)
FEATS = ["block4", "block8", "block16", "phaseR", "d0", "d1", "d2", "d3", "d4_7", "d8p", "block8_vs_7"]
CONDITIONS = {
    "stego, no key, full capacity": dict(kind="stego", key=None, frac=1.0),
    "stego, secret key, full capacity": dict(kind="stego", key="secret", frac=1.0),
    "stego, secret key, full, delta 24 (3b)": dict(kind="stego", key="secret", frac=1.0, delta=24.0),
    "stego, secret key, full, delta 16 (2b)": dict(kind="stego", key="secret", frac=1.0, delta=16.0),
    "stego, secret key, short message (16 %)": dict(kind="stego", key="secret", frac=0.16),
    "watermark alpha 8": dict(kind="wm", alpha=8),
    "watermark alpha 16": dict(kind="wm", alpha=16),
}


def blockiness(A, g):
    """mean |jump| across grid-g borders divided by mean |jump| elsewhere (rows and columns together)."""
    dx = np.abs(np.diff(A, axis=1))
    dy = np.abs(np.diff(A, axis=0))
    bx = np.zeros(dx.shape[1], bool)
    bx[g - 1 :: g] = True
    by = np.zeros(dy.shape[0], bool)
    by[g - 1 :: g] = True
    across = np.concatenate([dx[:, bx].ravel(), dy[by, :].ravel()]).mean()
    inside = np.concatenate([dx[:, ~bx].ravel(), dy[~by, :].ravel()]).mean()
    return across / max(inside, 1e-9)


def features(A):
    s1 = np.linalg.svd(stego.to_blocks(A, 8), compute_uv=False)[:, 0]
    R = max(float(np.abs(np.exp(2j * np.pi * s1 / d).mean())) for d in SCAN)
    d = np.abs(np.diff(A, axis=1)).ravel()
    hist = [
        np.mean(d == 0),
        np.mean(d == 1),
        np.mean(d == 2),
        np.mean(d == 3),
        np.mean((d >= 4) & (d < 8)),
        np.mean(d >= 8),
    ]
    b8 = blockiness(A, 8)
    return [blockiness(A, 4), b8, blockiness(A, 16), R] + hist + [b8 / blockiness(A, 7)]


def work(i):
    A = load_gray(IMGS["path"].iloc[i])
    rows = [
        dict(
            image=IMGS["filename"].iloc[i],
            role=IMGS["role"].iloc[i],
            condition="original",
            label=0,
            **dict(zip(FEATS, features(A), strict=True)),
        )
    ]
    rng = np.random.default_rng(i)
    k = min(A.shape)
    W = np.random.default_rng(7).integers(0, 2, (k, k)).astype(float)
    for name, c in CONDITIONS.items():
        if c["kind"] == "stego":
            n = int(c["frac"] * stego.capacity(A.shape, 8))
            B = stego.embed_bits(A, rng.integers(0, 2, n), c.get("delta", 32.0), 8, key=c["key"]).image
        else:
            B = np.clip(np.rint(watermark.embed(A, W, c["alpha"])[0]), 0, 255)
        rows.append(
            dict(
                image=IMGS["filename"].iloc[i],
                role=IMGS["role"].iloc[i],
                condition=name,
                label=1,
                **dict(zip(FEATS, features(B), strict=True)),
            )
        )
    return rows


def fit_logistic(X, y, lam=1e-2, steps=4000, lr=0.5):
    w = np.zeros(X.shape[1])
    b = 0.0
    for _ in range(steps):
        p = 1 / (1 + np.exp(-(X @ w + b)))
        w -= lr * (X.T @ (p - y) / len(y) + lam * w)
        b -= lr * float(np.mean(p - y))
    return w, b


if __name__ == "__main__":
    t0 = time.time()
    rows = []
    with Pool(2) as pool:
        for n, r in enumerate(pool.imap(work, range(len(IMGS))), 1):
            rows += r
            if n % 50 == 0:
                print(f"{n}/{len(IMGS)} images  {time.time() - t0:.0f}s", flush=True)
    F = pd.DataFrame(rows)
    F.to_csv(ROOT / "results" / "ml_features.csv", index=False, float_format="%.6g")
    out = []
    for name in CONDITIONS:
        D = F[F.condition.isin(["original", name])]
        tr, te = D[D.role == "train"], D[D.role == "test"]
        mu, sd = tr[FEATS].mean(), tr[FEATS].std().replace(0, 1)
        w, b = fit_logistic(((tr[FEATS] - mu) / sd).to_numpy(), tr.label.to_numpy().astype(float))
        sc = ((te[FEATS] - mu) / sd).to_numpy() @ w + b
        pos = te.label.to_numpy() == 1
        top = sorted(zip(FEATS, w, strict=True), key=lambda t: -abs(t[1]))[:3]
        out.append(
            dict(
                condition=name,
                test_auc=auc(sc[pos], sc[~pos]),
                test_accuracy=float(np.mean((sc > 0) == pos)),
                auc_blockiness8_alone=auc(te["block8"][pos], te["block8"][~pos]),
                auc_phaseR_alone=auc(te["phaseR"][pos], te["phaseR"][~pos]),
                top_features=", ".join(f"{f} ({v:+.2f})" for f, v in top),
            )
        )
    out = pd.DataFrame(out)
    out.to_csv(ROOT / "results" / "ml_steganalysis.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 80)
    print(out.round(3).to_string(index=False))
