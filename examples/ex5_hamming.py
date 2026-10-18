"""Section 4.5: Hamming(7,4) - encode, flip one bit, syndrome, correct."""

import numpy as np

from svdmark.ecc import G, H, decode, encode

print("G H^T (mod 2) =\n", (G @ H.T) % 2)
d = np.array([1, 0, 1, 1])
c = encode(d)
print("data d        =", d)
print("codeword c    =", c)

r = c.copy()
r[2] ^= 1  # bit 3 flips during transmission
print("received r    =", r)
print("syndrome H r  =", (H @ r) % 2, " = column 3 of H:", H[:, 2])
d_hat, fixed = decode(r)
print("decoded       =", d_hat, " bits corrected:", fixed)
