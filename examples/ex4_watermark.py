"""Section 4.4: Liu-Tan watermark, 2x2 example and 3x3 check."""

import numpy as np

from svdmark.metrics import ncc
from svdmark.watermark import embed, extract, shift_score

A = np.array([[3.0, 0.0], [4.0, 5.0]])
W = np.array([[1.0, 0.0], [1.0, 1.0]])
Aw, key = embed(A, W, alpha=0.5)
print("Sigma_w          =", np.round(key.Sw, 4))
print("A_w              =\n", np.round(Aw, 4))
print(
    "|A_w - A|_F      =",
    round(np.linalg.norm(Aw - A), 5),
    "  |sigma_w - sigma| =",
    round(np.linalg.norm(key.Sw - key.S), 5),
)
print("W* from A_w      =\n", np.round(extract(Aw, key), 4))

B = np.array([[100.0, 104, 98], [96, 100, 103], [101, 99, 97]])
Wx = np.array([[1.0, 0, 1], [0, 1, 0], [1, 0, 1]])
Bw, k3 = embed(B, Wx, alpha=4)
W_fake = extract(B, k3)  # extract from the image that was NEVER marked
print(
    "3x3 never marked: W*[1,3] =",
    round(W_fake[0, 2], 4),
    " NCC =",
    round(ncc(Wx, W_fake), 3),
    " shift =",
    shift_score(B, k3),
)
print(
    "3x3 marked:       NCC =",
    round(ncc(Wx, extract(Bw, k3)), 3),
    " shift =",
    round(shift_score(Bw, k3), 3),
)
