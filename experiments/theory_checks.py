"""Check the theory used in the report on real images (task #15).

1. Orthogonal invariance: ||A_w - A||_F == ||Sigma_w - Sigma||_F   (watermark, all 150 images)
2. Weyl:  max_i |sigma_i(A+E) - sigma_i(A)| <= ||E||_2             (8x8 blocks, Gaussian E)
3. Rounding rule:  pixel rounding gives |e| <= 0.5, so ||E||_2 <= b/2 and sigma moves < b/2;
   hence delta > b survives rounding.  Flip rate of embedded bits when only rounding noise is added.
4. Noise rule for sigma_1: drift ~ N(0, s^2)  ->  BER ~ 2 Q(delta / 2s).  Predicted vs measured.
Output: results/theory_checks.csv  (long format: check, params..., value)
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from svdmark import stego, watermark                        # noqa: E402
from svdmark.data import list_images, load_gray, sample_images  # noqa: E402

sample = sample_images(list_images(ROOT / "data" / "images"))
rows = []

# 1 ---------------------------------------------------------------- Frobenius identity
worst = {4: 0.0, 16: 0.0}
for p in sample["path"]:
    A = load_gray(p)
    k = min(A.shape)
    W = np.random.default_rng(7).integers(0, 2, (k, k)).astype(float)
    for alpha in worst:
        Aw, key = watermark.embed(A, W, alpha)
        lhs = np.linalg.norm(Aw - A)
        rhs = np.linalg.norm(key.Sw - key.S)
        worst[alpha] = max(worst[alpha], abs(lhs - rhs) / rhs)
for alpha, v in worst.items():
    rows.append(dict(check="frobenius_identity", b=0, alpha=alpha, value=v, note="max relative difference over 150 images"))

# 2 ---------------------------------------------------------------- Weyl on 8x8 blocks
imgs = [load_gray(p) for p in sample["path"].iloc[:20]]
rng = np.random.default_rng(5)
for s in (1, 2, 4, 8):
    ratio_max, drift1 = 0.0, []
    for A in imgs:
        blk = stego._to_blocks(A, 8)
        E = rng.normal(0, s, blk.shape)
        d = np.abs(np.linalg.svd(blk + E, compute_uv=False) - np.linalg.svd(blk, compute_uv=False))
        e2 = np.linalg.svd(E, compute_uv=False)[:, 0]
        ratio_max = max(ratio_max, float((d.max(axis=1) / e2).max()))
        drift1.append(d[:, 0])
    rows.append(dict(check="weyl_max_ratio", b=8, noise_std=s, value=ratio_max, note="max over blocks of max_i|dsigma_i| / ||E||_2 (must be <= 1)"))
    rows.append(dict(check="sigma1_drift_rms", b=8, noise_std=s, value=float(np.sqrt(np.mean(np.concatenate(drift1) ** 2))), note="rms drift of sigma_1"))

# 3 ---------------------------------------------------------------- rounding rule delta > b
for b in (4, 8, 16):
    for ratio in (0.25, 0.5, 1.0, 1.5, 2.0):
        delta = ratio * b
        flips = total = 0
        worst_drift = 0.0
        for A in imgs[:5]:
            blk = stego._to_blocks(A, b)
            U, s_, Vt = np.linalg.svd(blk)
            bits = rng.integers(0, 2, len(blk))
            new = np.array([stego.embed_value(v, int(bt), delta) for v, bt in zip(s_[:, 0], bits)])
            s2 = s_.copy(); s2[:, 0] = new
            marked = (U * s2[:, None, :]) @ Vt                     # float, not yet rounded
            err = rng.uniform(-0.5, 0.5, marked.shape)             # what rounding to integers does, worst-case-ish
            noisy = marked + err
            read = stego.extract_bit_array(np.linalg.svd(noisy, compute_uv=False)[:, 0], delta)
            flips += int((read != bits).sum()); total += len(bits)
            worst_drift = max(worst_drift, float(np.abs(np.linalg.svd(noisy, compute_uv=False)[:, 0] - new).max()))
        rows.append(dict(check="rounding_flip_pct", b=b, delta_over_b=ratio, value=100 * flips / total,
                         note=f"max sigma_1 drift {worst_drift:.3f}; guaranteed safe bound b/2 = {b / 2}"))

# 4 ---------------------------------------------------------------- noise rule for sigma_1
Q = lambda x: 0.5 * math.erfc(x / math.sqrt(2))
for b in (8,):
    for delta in (16, 24, 32, 48, 64):
        for s in (2, 4, 8):
            flips = total = 0
            for A in imgs:
                blk = stego._to_blocks(A, b)
                U, s_, Vt = np.linalg.svd(blk)
                bits = rng.integers(0, 2, len(blk))
                new = np.array([stego.embed_value(v, int(bt), delta) for v, bt in zip(s_[:, 0], bits)])
                s2 = s_.copy(); s2[:, 0] = new
                noisy = (U * s2[:, None, :]) @ Vt + rng.normal(0, s, blk.shape)
                read = stego.extract_bit_array(np.linalg.svd(noisy, compute_uv=False)[:, 0], delta)
                flips += int((read != bits).sum()); total += len(bits)
            rows.append(dict(check="noise_ber_measured", b=b, delta=delta, noise_std=s, value=100 * flips / total,
                             note="sigma_1, float pixels (no clipping, no rounding)"))
            rows.append(dict(check="noise_ber_predicted", b=b, delta=delta, noise_std=s, value=100 * 2 * Q(delta / (2 * s)),
                             note="2 Q(delta / 2s), drift ~ N(0, s^2)"))
out = pd.DataFrame(rows)
out.to_csv(ROOT / "results" / "theory_checks.csv", index=False, float_format="%.6g")
pd.set_option("display.width", 200)
for chk, g in out.groupby("check", sort=False):
    print("\n==", chk)
    print(g.drop(columns=["check"]).dropna(axis=1, how="all").round(4).to_string(index=False))
