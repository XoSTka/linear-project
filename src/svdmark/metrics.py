"""Quality / accuracy metrics: MSE, RMS, PSNR, NCC, BER."""
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


def ber(bits: np.ndarray, bits_hat: np.ndarray) -> float:
    """Bit error rate = wrong bits / total bits."""
    bits = np.asarray(bits).ravel()
    bits_hat = np.asarray(bits_hat).ravel()
    return float(np.mean(bits != bits_hat))
