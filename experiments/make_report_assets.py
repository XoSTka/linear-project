"""Build every figure (results/figures/*.png) and table (results/tables/*.csv + *.tex) for the report and slides.

Reads only CSV files in results/ (written by the full_*.py, theory_checks.py and steganalysis.py scripts),
so figures and tables always match the numbers on disk.  Run:  python experiments/make_report_assets.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
RES, FIG, TAB = ROOT / "results", ROOT / "results" / "figures", ROOT / "results" / "tables"
FIG.mkdir(exist_ok=True); TAB.mkdir(exist_ok=True)

from matplotlib.lines import Line2D
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"           # validated categorical slots 1-3
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
BCOL = {4: BLUE, 8: ORANGE, 16: AQUA}
BMARK = {4: "o", 8: "s", 16: "^"}
plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
                     "axes.titlesize": 11, "axes.titleweight": "bold", "savefig.dpi": 200, "savefig.bbox": "tight"})
FLOOR = 0.01                                                       # BER floor for log axes (percent)
ATT_ORDER = ["none", "noise1", "noise2", "noise4", "noise8", "jpeg95", "jpeg90", "jpeg75", "jpeg50", "crop0.05", "crop0.1", "crop0.25"]
ATT_LABEL = {"none": "none", "noise1": "noise\nσ=1", "noise2": "noise\nσ=2", "noise4": "noise\nσ=4", "noise8": "noise\nσ=8",
             "jpeg95": "JPEG\nQ95", "jpeg90": "JPEG\nQ90", "jpeg75": "JPEG\nQ75", "jpeg50": "JPEG\nQ50",
             "crop0.05": "crop\n5%", "crop0.1": "crop\n10%", "crop0.25": "crop\n25%"}


def save_table(df, name, caption, fmt=None):
    df.to_csv(TAB / f"{name}.csv", index=False, float_format="%.4g")
    tex = df.to_latex(index=False, float_format=lambda x: f"{x:.3g}", escape=True,
                      caption=caption, label=f"tab:{name}", position="htbp")
    (TAB / f"{name}.tex").write_text(tex, encoding="utf-8")


st = pd.read_csv(RES / "stego_summary.csv")
wm = pd.read_csv(RES / "watermark_summary.csv")
det = pd.read_csv(RES / "watermark_detection.csv")
th = pd.read_csv(RES / "theory_checks.csv")
sa = pd.read_csv(RES / "steganalysis_summary.csv")
wf = pd.read_csv(RES / "watermark_full.csv")

# ---------------------------------------------------------------- F1 stego trade-off (PSNR vs BER)
fig, axes = plt.subplots(1, 2, figsize=(10, 4.0), sharey=True)
for ax, att, title in zip(axes, ["noise4", "jpeg75"], ["Gaussian noise σ = 4", "JPEG quality 75"]):
    a = st[st.attack == att]
    for (b, k), g in a.groupby(["b", "k"]):
        ax.scatter(g.psnr, g.ber_mean.clip(lower=FLOOR), s=46, marker=BMARK[b], color=BCOL[b],
                   facecolor=BCOL[b] if k == 0 else "white", linewidths=1.6, zorder=3)
    ax.axvline(40, color=MUTED, ls="--", lw=1)
    ax.text(40.3, FLOOR * 0.85, "40 dB target", color=MUTED, fontsize=9, va="bottom")
    ax.set_yscale("log"); ax.set_xlabel("PSNR of stego image (dB)  →  better quality"); ax.set_title(title)
axes[0].set_ylabel("Bit error rate (%)  ↓ better")
axes[0].set_ylim(FLOOR * 0.7, 80)
h = [Line2D([], [], marker=BMARK[b], color=BCOL[b], ls="", markersize=7, label=f"b = {b}  ({(320*480)//(b*b):,} bits)") for b in (4, 8, 16)]
h += [Line2D([], [], marker="o", color=MUTED, ls="", markersize=7, label="σ₁ (filled)"),
      Line2D([], [], marker="o", color=MUTED, markerfacecolor="white", ls="", markersize=7, label="σ₂ (hollow)")]
fig.legend(handles=h, loc="lower center", ncol=5, frameon=False, fontsize=9, bbox_to_anchor=(0.5, -0.13))
fig.suptitle("Steganography: each point is one (block size, Δ, σ index); mean over 150 images", y=1.02, fontsize=11)
fig.savefig(FIG / "fig_stego_tradeoff.png"); plt.close(fig)

# ---------------------------------------------------------------- F2 BER vs attack strength at ~40.7 dB (delta = 4b, sigma_1)
fig, axes = plt.subplots(1, 3, figsize=(11, 3.8), sharey=True, gridspec_kw={"width_ratios": [4, 4, 3]})
groups = [("noise", ["noise1", "noise2", "noise4", "noise8"], ["1", "2", "4", "8"], "Gaussian noise, std (grey levels)"),
          ("jpeg", ["jpeg95", "jpeg90", "jpeg75", "jpeg50"], ["95", "90", "75", "50"], "JPEG quality factor"),
          ("crop", ["crop0.05", "crop0.1", "crop0.25"], ["5", "10", "25"], "Area removed (%)")]
for ax, (_, atts, labs, xl) in zip(axes, groups):
    for b in (4, 8, 16):
        g = st[(st.k == 0) & (st.b == b) & (st.c == 4)].set_index("attack").loc[atts]
        ax.plot(range(len(atts)), g.ber_mean.clip(lower=FLOOR), marker=BMARK[b], color=BCOL[b], lw=2, ms=6, label=f"b = {b}")
        if len(atts) == 4:
            ax.annotate(f"b={b}", (len(atts) - 1, max(g.ber_mean.iloc[-1], FLOOR)), xytext=(6, 0), textcoords="offset points",
                        color=BCOL[b], fontsize=9, va="center")
    ax.set_xticks(range(len(atts))); ax.set_xticklabels(labs); ax.set_xlabel(xl); ax.set_yscale("log"); ax.set_xlim(-0.2, len(atts) - 0.35)
axes[0].set_ylabel("Bit error rate (%)"); axes[0].set_ylim(FLOOR * 0.7, 80)
axes[2].text(0.5, 0.06, "all three block sizes overlap:\nBER ≈ half of the removed area", transform=axes[2].transAxes, fontsize=8.5, color=MUTED, ha="center")
axes[2].legend(handles=[Line2D([], [], marker=BMARK[b], color=BCOL[b], lw=2, label=f"b={b}") for b in (4, 8, 16)], frameon=False, fontsize=8.5, loc="upper left")
fig.suptitle("Steganography at equal image quality (Δ = 4b, σ₁, PSNR ≈ 40.7 dB): noise and JPEG favour large blocks; crop hurts all", y=1.02, fontsize=11)
fig.savefig(FIG / "fig_stego_attacks.png"); plt.close(fig)

# ---------------------------------------------------------------- F3 watermark detection heatmaps (AUC)
fig, axes = plt.subplots(1, 2, figsize=(14, 3.8), sharey=True)
alphas = [4, 8, 12, 16, 24]
for ax, col, title in zip(axes, ["auc_ncc_same", "auc_shift_same"],
                          ["NCC of the extracted mark (Liu–Tan)", "Singular-value shift score (ours)"]):
    m = det[det.alpha.isin(alphas)].pivot(index="alpha", columns="attack", values=col).loc[alphas, ATT_ORDER]
    im = ax.imshow(m.values, vmin=0, vmax=1, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(ATT_ORDER))); ax.set_xticklabels([ATT_LABEL[a] for a in ATT_ORDER], fontsize=7)
    ax.set_yticks(range(len(alphas))); ax.set_yticklabels([f"α = {a}" for a in alphas]); ax.grid(False); ax.set_title(title)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8, color="white" if v > 0.6 else INK)
fig.colorbar(im, ax=axes, shrink=0.85, label="AUC (0.5 = coin flip, 1 = perfect)")
fig.suptitle("Can the detector tell a watermarked image from the SAME image never watermarked? (both attacked equally; 150 images)", y=1.04, fontsize=11)
fig.savefig(FIG / "fig_watermark_detection.png"); plt.close(fig)

# ---------------------------------------------------------------- F4 watermark quality vs alpha
q = wf[wf.attack == "none"].groupby("alpha").agg(mean=("psnr_u8", "mean"), lo=("psnr_u8", "min"), hi=("psnr_u8", "max"),
                                                  pass40=("psnr_u8", lambda x: 100 * (x >= 40).mean()))
fig, ax = plt.subplots(figsize=(6.4, 3.8))
ax.fill_between(q.index, q.lo, q.hi, color=BLUE, alpha=0.18, lw=0)
ax.plot(q.index, q["mean"], color=BLUE, marker="o", lw=2)
ax.axhline(40, color=MUTED, ls="--", lw=1); ax.text(2.3, 40.8, "40 dB target", color=MUTED, fontsize=9)
for a, r in q.iterrows():
    ax.annotate(f"{r.pass40:.0f}% ≥ 40 dB", (a, r["mean"]), xytext=(8 if a == 2 else 0, 10), textcoords="offset points",
                ha="left" if a == 2 else "center", fontsize=8.5, color=INK)
ax.set_xscale("log", base=2); ax.set_xticks(q.index); ax.set_xticklabels([str(a) for a in q.index])
ax.set_xlabel("Watermark strength α"); ax.set_ylabel("PSNR after saving as 8-bit (dB)")
ax.set_title("Watermark quality: mean and min–max over 150 images")
fig.savefig(FIG / "fig_watermark_psnr.png"); plt.close(fig)

# ---------------------------------------------------------------- F5 theory: predicted vs measured BER
p = th[th.check == "noise_ber_predicted"].set_index(["delta", "noise_std"]).value
m = th[th.check == "noise_ber_measured"].set_index(["delta", "noise_std"]).value
fig, ax = plt.subplots(figsize=(4.8, 4.4))
lim = [0.001, 60]
ax.plot(lim, lim, color=MUTED, lw=1, ls="--"); ax.text(0.0015, 0.0035, "perfect agreement", color=MUTED, fontsize=8.5, rotation=36)
sc = {2: BLUE, 4: ORANGE, 8: AQUA}
for (d, s), pv in p.items():
    mv = m[(d, s)]
    if pv >= lim[0] and mv >= lim[0]:
        ax.scatter(pv, mv, s=48, color=sc[int(s)], zorder=3)
for s, c in sc.items():
    ax.scatter([], [], color=c, label=f"noise σ = {s}")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("Predicted BER (%)   2Q(Δ / 2σ)"); ax.set_ylabel("Measured BER (%)"); ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.set_title("Theory vs experiment (σ₁, b = 8)")
fig.savefig(FIG / "fig_theory_ber.png"); plt.close(fig)

# ---------------------------------------------------------------- F6 steganalysis histograms (one image)
from svdmark import stego
from svdmark.data import list_images, load_gray, sample_images
img = load_gray(sample_images(list_images(ROOT / "data" / "images"))["path"].iloc[3])
bits = np.random.default_rng(3).integers(0, 2, stego.capacity(img.shape, 8))
D = 32
variants = [("Original", img), ("Stego, no key", stego.embed_bits(img, bits, D, 8, 0).image),
            ("Stego, with secret key", stego.embed_bits(img, bits, D, 8, 0, key="secret").image)]
fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.2), sharey=True)
for ax, (name, A) in zip(axes, variants):
    s1 = np.linalg.svd(stego._to_blocks(A, 8), compute_uv=False)[:, 0]
    ax.hist((s1 / D) % 1, bins=20, range=(0, 1), color=BLUE if name != "Stego, no key" else ORANGE, edgecolor="white")
    ax.set_title(name); ax.set_xlabel("position of σ₁ inside its Δ-interval")
axes[0].set_ylabel("number of blocks")
fig.suptitle("What a simple statistic sees (Δ = 32, b = 8): without a key the values pile up at the interval centre", y=1.04, fontsize=11)
fig.savefig(FIG / "fig_steganalysis.png"); plt.close(fig)

# ---------------------------------------------------------------- tables
t = st[(st.k == 0) & st.attack.isin(["none", "noise2", "noise4", "noise8", "jpeg90", "jpeg75", "jpeg50", "crop0.1"])]
t = t.pivot_table(index=["b", "delta", "bits", "psnr", "pass40"], columns="attack", values="ber_mean").reset_index()
t = t[["b", "delta", "bits", "psnr", "pass40", "none", "noise2", "noise4", "noise8", "jpeg90", "jpeg75", "jpeg50", "crop0.1"]]
t.columns = ["b", "Delta", "bits", "PSNR (dB)", "share >=40 dB", "none", "noise s=2", "noise s=4", "noise s=8", "JPEG 90", "JPEG 75", "JPEG 50", "crop 10%"]
save_table(t, "stego_sigma1", "Steganography with $\\sigma_1$: PSNR and mean BER (\\%) under attack, 150 images.")

t = st[(st.k == 1) & (st.c == 4) & st.attack.isin(["none", "noise4", "jpeg75"])]
t = t.pivot_table(index=["b", "delta", "psnr", "pass40", "failed_pct"], columns="attack", values="ber_mean").reset_index()
t.columns = ["b", "Delta", "PSNR (dB)", "share >=40 dB", "blocks failing check (%)", "BER none", "BER noise s=4", "BER JPEG 75"]
save_table(t, "stego_sigma2", "Steganography with $\\sigma_2$ at $\\Delta=4b$ (for comparison with $\\sigma_1$).")

w = wm[wm.attack.isin(["none", "noise4", "jpeg75"])].pivot_table(index="alpha", columns="attack", values=["ncc_mean", "fp_ncc_mean", "ber_mean"])
w.columns = [f"{a}_{b}" for a, b in w.columns]
w = w.reset_index()
dd = det[det.attack.isin(["noise4", "jpeg75"])].pivot_table(index="alpha", columns="attack", values=["auc_ncc_same", "auc_shift_same"])
dd.columns = [f"{a}_{b}" for a, b in dd.columns]
w = w.merge(dd.reset_index(), on="alpha").merge(q.reset_index()[["alpha", "mean", "pass40"]], on="alpha")
w = w[["alpha", "mean", "pass40", "ncc_mean_none", "fp_ncc_mean_none", "ncc_mean_noise4", "ncc_mean_jpeg75",
       "auc_ncc_same_noise4", "auc_shift_same_noise4", "auc_ncc_same_jpeg75", "auc_shift_same_jpeg75"]]
w.columns = ["alpha", "PSNR (dB)", "share >=40 dB (%)", "NCC marked", "NCC never-marked", "NCC marked, noise s=4", "NCC marked, JPEG 75",
             "AUC NCC noise 4", "AUC shift noise 4", "AUC NCC JPEG 75", "AUC shift JPEG 75"]
save_table(w, "watermark", "Watermarking (Liu--Tan): quality, NCC, and ability to separate marked from never-marked images (AUC), 150 images.")

tt = th[th.check.isin(["noise_ber_measured", "noise_ber_predicted"])].pivot_table(index=["delta", "noise_std"], columns="check", values="value").reset_index()
tt = tt[(tt.noise_ber_measured > 0.001) | (tt.noise_ber_predicted > 0.001)]
tt.columns = ["Delta", "noise s", "measured BER (%)", "predicted BER (%)"]
save_table(tt, "theory_noise", "Predicted $2Q(\\Delta/2s)$ against measured BER for $\\sigma_1$, $b=8$.")

s2 = sa.copy()
s2.columns = ["sigma index k (0=sigma1)", "Delta", "mode", "R known (orig)", "R known (stego)", "AUC known", "R blind (orig)", "R blind (stego)", "AUC blind"]
save_table(s2, "steganalysis", "Detection of stego images by the phase-concentration statistic; AUC 0.5 means the statistic cannot tell them apart.")
print("figures:", sorted(p.name for p in FIG.glob("*.png")))
print("tables:", sorted(p.name for p in TAB.glob("*.tex")))
