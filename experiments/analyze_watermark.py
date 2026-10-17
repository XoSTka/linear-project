"""Summaries of results/watermark_full.csv.

Writes results/watermark_summary.csv (mean/sd per alpha x attack) and
results/watermark_detection.csv (AUC of NCC vs shift_score for marked-vs-never-marked).
AUC = P(score of a marked image > score of a never-marked image), ties count 1/2.
"""

from pathlib import Path

import pandas as pd

from svdmark import attacks
from svdmark.metrics import auc

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "results" / "watermark_full.csv")


order = [attacks.label(n, lv) for n, lv in attacks.all_attacks()]
d["attack"] = pd.Categorical(d["attack"], order, ordered=True)

# --- summary: mean and sd over all evaluation images
cols = ["psnr_u8", "ncc", "ncc_c", "ber", "shift", "fp_ncc", "fp_ber", "fp_shift", "other_ncc", "other_shift"]
g = d.groupby(["alpha", "attack"], observed=True)[cols]
summ = g.mean().add_suffix("_mean").join(g.std().add_suffix("_sd")).reset_index()
summ.to_csv(ROOT / "results" / "watermark_summary.csv", index=False, float_format="%.5g")

# --- detection: marked (attacked) vs never-marked (same attack): same image, and other image
rows = []
for (alpha, att), s in d.groupby(["alpha", "attack"], observed=True):
    rows.append(
        dict(
            alpha=alpha,
            attack=att,
            auc_ncc_same=auc(s["ncc"], s["fp_ncc"]),
            auc_shift_same=auc(s["shift"], s["fp_shift"]),
            auc_ncc_other=auc(s["ncc"], s["other_ncc"]),
            auc_shift_other=auc(s["shift"], s["other_shift"]),
        )
    )
det = pd.DataFrame(rows)
det.to_csv(ROOT / "results" / "watermark_detection.csv", index=False, float_format="%.4f")

pd.set_option("display.width", 220)
print("images:", d["image"].nunique(), " rows:", len(d))
print("\nMean PSNR (8-bit) and identical-to-original share, by alpha")
print(
    d[d.attack == "none"]
    .groupby("alpha")
    .agg(
        psnr=("psnr_u8", "mean"),
        min_psnr=("psnr_u8", "min"),
        identical=("identical", "mean"),
        pass40=("psnr_u8", lambda x: (x >= 40).mean()),
    )
    .round(3)
)
print("\nNCC of extracted mark (marked image) / NCC from never-marked SAME image")
print(summ.pivot(index="attack", columns="alpha", values="ncc_mean").round(3))
print(summ.pivot(index="attack", columns="alpha", values="fp_ncc_mean").round(3))
print("\nBER % of extracted mark")
print((100 * summ.pivot(index="attack", columns="alpha", values="ber_mean")).round(2))
print("\nAUC  NCC  marked vs never-marked SAME image")
print(det.pivot(index="attack", columns="alpha", values="auc_ncc_same").round(3))
print("\nAUC  shift_score  marked vs never-marked SAME image")
print(det.pivot(index="attack", columns="alpha", values="auc_shift_same").round(3))
print("\nAUC  NCC  marked vs OTHER image")
print(det.pivot(index="attack", columns="alpha", values="auc_ncc_other").round(3))
print("\nAUC  shift_score  marked vs OTHER image")
print(det.pivot(index="attack", columns="alpha", values="auc_shift_other").round(3))
