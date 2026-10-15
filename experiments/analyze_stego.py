"""Summaries of results/stego_full.csv (task #8).  Writes results/stego_summary.csv."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "results" / "stego_full.csv")
order = ["none", "noise1", "noise2", "noise4", "noise8", "jpeg95", "jpeg90", "jpeg75", "jpeg50", "crop0.05", "crop0.1", "crop0.25"]
d["attack"] = pd.Categorical(d["attack"], order, ordered=True)
keys = ["k", "b", "delta", "c", "bits", "attack"]
g = d.groupby(keys, observed=True)
s = g["ber"].agg(ber_mean="mean", ber_sd="std", ber_median="median").join(
    g[["psnr", "failed_pct"]].mean()).join(
    g["psnr"].agg(psnr_min="min", pass40=lambda x: (x >= 40).mean())).reset_index()
s.to_csv(ROOT / "results" / "stego_summary.csv", index=False, float_format="%.5g")

pd.set_option("display.width", 250)
q = s[s.attack == "none"].drop(columns=["attack"])
print("images:", d["image"].nunique(), " rows:", len(d))
print("\nNo attack: PSNR, share of images with PSNR>=40, failed blocks %, BER %")
print(q[["k", "b", "delta", "bits", "psnr", "psnr_min", "pass40", "failed_pct", "ber_mean"]].round(3).to_string(index=False))
for k in (0, 1):
    print(f"\nBER % (mean of 150 images), k={k}  (rows: b/delta, columns: attack)")
    t = s[s.k == k].pivot_table(index=["b", "delta"], columns="attack", values="ber_mean", observed=True)
    print(t.round(2).to_string())
