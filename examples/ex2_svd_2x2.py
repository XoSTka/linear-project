"""Section 4.2: SVD of A = [[3,0],[4,5]] by hand and with numpy."""

import numpy as np

from svdmark.svd_utils import reconstruct, svd, svd_2x2_by_hand

A = np.array([[3.0, 0.0], [4.0, 5.0]])
print("A^T A =\n", A.T @ A)
print("eigenvalues of A^T A =", np.linalg.eigvalsh(A.T @ A)[::-1])

U, s, Vt = svd_2x2_by_hand(A)
print("by hand: sigma =", np.round(s, 4))
print("         u1 =", np.round(U[:, 0], 4), " v1 =", np.round(Vt[0], 4))
print("numpy:   sigma =", np.round(svd(A)[1], 4))

print(
    "sigma1 u1 v1^T + sigma2 u2 v2^T =\n",
    np.round(reconstruct(U, s, Vt), 10),
)
print(
    "|A|_F^2 =",
    np.sum(A**2),
    "  sigma1^2 + sigma2^2 =",
    round(np.sum(s**2), 10),
)
