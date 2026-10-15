"""Pick the 150-image experiment set and save its full-image singular values.

Run from the project root:  python experiments/prepare_data.py
Writes  results/sample150.csv        (split, filename)
        results/sigma_150.csv        (one row per image, columns s1..s320)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from svdmark.data import list_images, load_gray, sample_images  # noqa: E402

df = sample_images(list_images(ROOT / "data" / "images"))
df[["split", "filename"]].to_csv(ROOT / "results" / "sample150.csv", index=False)

rows = []
for p in df["path"]:
    rows.append(np.linalg.svd(load_gray(p), compute_uv=False))
sig = pd.DataFrame(rows, columns=[f"s{i+1}" for i in range(len(rows[0]))])
sig.insert(0, "filename", df["filename"])
sig.to_csv(ROOT / "results" / "sigma_150.csv", index=False, float_format="%.6g")

print(df["split"].value_counts().to_string())
print("matrix shape:", sig.shape[0], "images x", sig.shape[1] - 1, "singular values")
