"""Fix the two image sets and save the full-image singular values of the evaluation set.

    pilot set : the 100 BSDS500 `val` images          -> only for choosing parameters (pilot_*.py)
    eval set  : the 400 BSDS500 `train` + `test` images -> every reported number (full_*.py, ...)

Run from the project root:  python experiments/prepare_data.py
Writes  results/image_sets.csv     (role, split, filename)  -- 500 rows
        results/sigma_eval.csv     (one row per evaluation image, columns s1..s320)
"""

from pathlib import Path

import numpy as np
import pandas as pd

from svdmark.data import eval_set, list_images, load_gray, pilot_set

ROOT = Path(__file__).resolve().parents[1]

df = list_images(ROOT / "data" / "images")
pil, ev = pilot_set(df), eval_set(df)
sets = pd.concat([pil.assign(role="pilot"), ev.assign(role="eval")])[["role", "split", "filename"]]
sets.to_csv(ROOT / "results" / "image_sets.csv", index=False)

rows = [np.linalg.svd(load_gray(p), compute_uv=False) for p in ev["path"]]
sig = pd.DataFrame(rows, columns=[f"s{i + 1}" for i in range(len(rows[0]))])
sig.insert(0, "filename", ev["filename"])
sig.to_csv(ROOT / "results" / "sigma_eval.csv", index=False, float_format="%.6g")

print(sets.groupby(["role", "split"]).size().to_string())
print("sigma matrix:", sig.shape[0], "images x", sig.shape[1] - 1, "singular values")
