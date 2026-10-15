"""Liu-Tan (2002) SVD watermarking:  D = S + alpha W,  D = Uw Sw Vw^T,  A_w = U Sw V^T.

The key needed to extract is (U, Vt, S, Uw, Vwt); extraction uses the *attacked*
image's singular values:  D* = Uw diag(S*) Vw^T,  W* = (D* - S) / alpha.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .svd_utils import reconstruct, svd


@dataclass(frozen=True)
class WatermarkKey:
    U: np.ndarray
    Vt: np.ndarray
    S: np.ndarray          # singular values of the original image, as a vector
    Uw: np.ndarray
    Vwt: np.ndarray
    alpha: float
    Sw: np.ndarray         # singular values of D = S + alpha W (= those of the marked image)


def embed(A: np.ndarray, W: np.ndarray, alpha: float) -> tuple[np.ndarray, WatermarkKey]:
    """Embed watermark W (same shape as diag(S), i.e. k x k) into image A."""
    U, s, Vt = svd(A)
    k = len(s)
    if W.shape != (k, k):
        raise ValueError(f"W must be {k}x{k} for an image whose rank bound is {k}")
    D = np.diag(s) + alpha * np.asarray(W, dtype=float)
    Uw, sw, Vwt = svd(D)
    Aw = reconstruct(U, sw, Vt)
    return Aw, WatermarkKey(U, Vt, s, Uw, Vwt, alpha, sw)


def singular_values(A: np.ndarray) -> np.ndarray:
    return np.linalg.svd(np.asarray(A, dtype=float), compute_uv=False)


def extract_from_sigma(s_star: np.ndarray, key: WatermarkKey) -> np.ndarray:
    """Extraction step given the received image's singular values (lets callers reuse one SVD)."""
    D_star = reconstruct(key.Uw, s_star, key.Vwt)
    return (D_star - np.diag(key.S)) / key.alpha


def extract(A_attacked: np.ndarray, key: WatermarkKey) -> np.ndarray:
    """Recover the (float) watermark estimate W* from a possibly attacked image."""
    return extract_from_sigma(singular_values(A_attacked), key)


def shift_score(A_received: np.ndarray, key: WatermarkKey) -> float:
    """Key-free evidence that the image really carries the mark (our addition, not Liu-Tan).

    Plain NCC of W* is dominated by the key (Uw, Vw): an image that was never marked,
    but whose singular values are close to S, still "extracts" W.  Here we ask instead
    whether the *singular values* moved the way embedding moves them:
        cos( sigma(received) - S ,  Sw - S )
    which is 1 for a marked image, and 0 (nothing moved) for the untouched original.
    """
    return shift_from_sigma(singular_values(A_received), key)


def shift_from_sigma(s_star: np.ndarray, key: WatermarkKey) -> float:
    v, t = s_star - key.S, key.Sw - key.S
    if np.linalg.norm(v) < 1e-9 * np.linalg.norm(key.S):      # nothing moved (numerical noise only)
        return 0.0
    denom = np.linalg.norm(v) * np.linalg.norm(t)
    return float(v @ t / denom) if denom else 0.0
