"""Summaries of results/stego_full.csv.  Writes results/stego_summary.csv."""

from pathlib import Path

import pandas as pd

from svdmark import attacks

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "results" / "stego_full.csv")
order = [attacks.label(n, lv) for n, lv in attacks.all_attacks()]
d["attack"] = pd.Categorical(d["attack"], order, ordered=True)
keys = ["k", "b", "delta", "c", "bits", "attack"]
g = d.groupby(keys, observed=True)
s = (
    g["ber"]
    .agg(ber_mean="mean", ber_sd="std", ber_median="median")
    .join(g[["psnr", "failed_pct"]].mean())
    .join(g["psnr"].agg(psnr_min="min", pass40=lambda x: (x >= 40).mean()))
    .reset_index()
)
s.to_csv(ROOT / "results" / "stego_summary.csv", index=False, float_format="%.5g")

pd.set_option("display.width", 250)
q = s[s.attack == "none"].drop(columns=["attack"])
print("images:", d["image"].nunique(), " rows:", len(d))
print("\nNo attack: PSNR, share of images with PSNR>=40, failed blocks %, BER %")
print(
    q[["k", "b", "delta", "bits", "psnr", "psnr_min", "pass40", "failed_pct", "ber_mean"]]
    .round(3)
    .to_string(index=False)
)
for k in (0, 1):
    print(f"\nBER % (mean of {d['image'].nunique()} images), k={k}  (rows: b/delta, columns: attack)")
    t = s[s.k == k].pivot_table(index=["b", "delta"], columns="attack", values="ber_mean", observed=True)
    print(t.round(2).to_string())
