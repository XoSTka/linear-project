"""Section 4.1: norm, dot product, cosine (NCC), bits mod 2."""

import numpy as np

from svdmark.metrics import ncc

ones = np.array([1.0, 1.0, 1.0])
print("|(1,1,1)|          =", round(np.linalg.norm(ones), 4))
print("unit vector        =", np.round(ones / np.linalg.norm(ones), 3))

v1 = np.array([1, 1]) / np.sqrt(2)
v2 = np.array([1, -1]) / np.sqrt(2)
print(
    "<v1, v2>           =",
    abs(round(v1 @ v2, 10)),
    " |v1| =",
    round(np.linalg.norm(v1), 4),
)

W = np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]])
W_star = np.array([[0, 0, 1], [0, 0, 0], [1, 0, 0]])
print("<W, W*>            =", int(W.ravel() @ W_star.ravel()))
print("NCC(W, W*)         =", round(ncc(W, W_star), 3))

a, b = np.array([1, 0, 1, 1]), np.array([1, 1, 0, 1])
print("a + b (mod 2)      =", (a + b) % 2)
print("a . b (mod 2)      =", (a @ b) % 2)
