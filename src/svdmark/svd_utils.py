"""SVD helpers: numpy wrapper, reconstruction, and a by-hand 2x2 SVD.

The by-hand version follows the textbook route used in the report:
    A^T A v_i = sigma_i^2 v_i,   sigma_i = sqrt(lambda_i),   u_i = A v_i / sigma_i
so that the hand calculation (Example 1) can be checked against numpy.
"""
from __future__ import annotations

import numpy as np


def svd(A: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Thin SVD, A = U @ diag(s) @ Vt, with s sorted high -> low."""
    A = np.asarray(A, dtype=float)
    return np.linalg.svd(A, full_matrices=False)


def reconstruct(U: np.ndarray, s: np.ndarray, Vt: np.ndarray) -> np.ndarray:
    """Rebuild a matrix from its SVD factors: U diag(s) V^T."""
    return (U * s) @ Vt


def energy(s: np.ndarray) -> float:
    """Total energy sum(sigma_i^2); equals the squared Frobenius norm of A."""
    return float(np.sum(np.square(s)))


def energy_fraction(s: np.ndarray, k: int = 1) -> float:
    """Share of the total energy held by the first k singular values."""
    s2 = np.square(s)
    return float(s2[:k].sum() / s2.sum())


def svd_2x2_by_hand(A: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """SVD of a real 2x2 matrix through the eigen-problem of A^T A.

    Returns (U, s, Vt) with s sorted high -> low.  Signs of the singular
    vectors are arbitrary (as in any SVD); the product U diag(s) Vt is exact.
    """
    A = np.asarray(A, dtype=float)
    if A.shape != (2, 2):
        raise ValueError("svd_2x2_by_hand expects a 2x2 matrix")

    G = A.T @ A                                  # symmetric, 2x2
    a, b, c = G[0, 0], G[0, 1], G[1, 1]
    mid = (a + c) / 2.0
    rad = np.hypot((a - c) / 2.0, b)             # closed-form eigenvalues of [[a,b],[b,c]]
    lam = np.array([mid + rad, max(mid - rad, 0.0)])
    s = np.sqrt(lam)

    # unit eigenvector for lam[0]; the second is its orthogonal complement
    if abs(b) > 1e-12:
        v1 = np.array([lam[0] - c, b])
    else:
        v1 = np.array([1.0, 0.0]) if a >= c else np.array([0.0, 1.0])
    v1 = v1 / np.linalg.norm(v1)
    v2 = np.array([-v1[1], v1[0]])
    V = np.column_stack([v1, v2])

    U = np.eye(2)
    if s[0] > 1e-12:
        U[:, 0] = A @ v1 / s[0]
    else:                                        # zero matrix: any orthonormal U works
        return U, s, V.T
    if s[1] > 1e-12:
        U[:, 1] = A @ v2 / s[1]
    else:                                        # rank 1: complete U orthonormally
        U[:, 1] = np.array([-U[1, 0], U[0, 0]])
    return U, s, V.T
