"""Section 4.3: hide bit 1 in sigma_1 of a 2x2 block, delta = 6."""

import numpy as np

from svdmark.metrics import psnr
from svdmark.stego import embed_value, extract_bit
from svdmark.svd_utils import reconstruct, svd

B = np.array([[52.0, 55.0], [61.0, 59.0]])
U, s, Vt = svd(B)
print("sigma            =", np.round(s, 3))
print(
    "bit now          =",
    extract_bit(s[0], 6),
    f"(interval {int(s[0] // 6)})",
)

s_new = s.copy()
s_new[0] = embed_value(s[0], 1, 6)  # centre of the nearest odd interval
print("new sigma1       =", s_new[0])
B_new = reconstruct(U, s_new, Vt)
print("B' (before round)=\n", np.round(B_new, 2))
B_int = np.rint(B_new)
print("B' (rounded)     =\n", B_int)

s_read = svd(B_int)[1][0]  # what the receiver sees
print(
    "receiver sigma1  =",
    round(s_read, 2),
    " -> bit",
    extract_bit(s_read, 6),
)
print("PSNR             =", round(psnr(B, B_int), 2), "dB")
