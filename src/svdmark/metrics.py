"""Quality / accuracy metrics: MSE, RMS, PSNR, NCC, BER, and the AUC used for detection tests."""

from __future__ import annotations

import numpy as np


def mse(a: np.ndarray, b: np.ndarray) -> float:
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    return float(np.mean(d * d))


def rms(a: np.ndarray, b: np.ndarray) -> float:
    """Root-mean-square pixel difference, sqrt(MSE)."""
    return float(np.sqrt(mse(a, b)))


def psnr(a: np.ndarray, b: np.ndarray, peak: float = 255.0) -> float:
    """PSNR in dB = 10 log10(peak^2 / MSE); inf when the images are identical."""
    m = mse(a, b)
    return float("inf") if m == 0 else float(10.0 * np.log10(peak * peak / m))


def ncc(w: np.ndarray, w_hat: np.ndarray) -> float:
    """Normalised correlation <w, w*> / (|w| |w*|) (cosine similarity)."""
    w = np.asarray(w, dtype=float).ravel()
    w_hat = np.asarray(w_hat, dtype=float).ravel()
    denom = np.linalg.norm(w) * np.linalg.norm(w_hat)
    return float(w @ w_hat / denom) if denom else 0.0


def ncc_centered(w: np.ndarray, w_hat: np.ndarray) -> float:
    """NCC after removing each matrix's mean (Pearson correlation).

    Plain NCC of two 0/1 marks is already about 0.5 for unrelated marks, because both are all-positive;
    removing the means makes unrelated marks score about 0.
    """
    w = np.asarray(w, dtype=float)
    w_hat = np.asarray(w_hat, dtype=float)
    return ncc(w - w.mean(), w_hat - w_hat.mean())


def ber(bits: np.ndarray, bits_hat: np.ndarray) -> float:
    """Bit error rate = wrong bits / total bits."""
    bits = np.asarray(bits).ravel()
    bits_hat = np.asarray(bits_hat).ravel()
    return float(np.mean(bits != bits_hat))


def auc(pos, neg) -> float:
    """Area under the ROC curve = P(a positive scores higher than a negative), ties count 1/2.

    Same value as the rank (Mann-Whitney) formula.  0.5 = the score cannot tell the two groups apart,
    1 = every positive above every negative, 0 = every positive below (which is also perfect separation).
    """
    pos = np.asarray(pos, dtype=float).ravel()
    neg = np.sort(np.asarray(neg, dtype=float).ravel())
    below = np.searchsorted(neg, pos, side="left")  # negatives strictly lower than each positive
    tied = np.searchsorted(neg, pos, side="right") - below  # negatives equal to it
    return float((below.sum() + 0.5 * tied.sum()) / (len(pos) * len(neg)))
