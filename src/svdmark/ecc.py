"""Hamming(7,4) error-correcting code -- linear algebra over the two-element field {0, 1} (arithmetic mod 2).

Why: one wrong bit makes the CRC fail and the whole message is refused.  Hamming(7,4) adds 3 check bits to
every 4 data bits, so ANY single wrong bit inside a 7-bit codeword can be found and flipped back.

    data   d = [d1 d2 d3 d4]                  (row vector, 4 bits)
    encode c = d G  (mod 2)                   (7 bits; G = [I4 | P] keeps the data bits in front)
    check  s = H r^T (mod 2)                  (3 bits, the "syndrome" of the received word r)
           s = 0            -> no error found
           s = column j of H -> bit j is wrong: flip it
Every column of H is a different non-zero 3-bit vector, so each single-bit error has its own syndrome.
Two or more errors in one codeword cannot be corrected (the CRC then still catches the message).
"""

from __future__ import annotations

import numpy as np

P = np.array([[1, 1, 0], [1, 0, 1], [0, 1, 1], [1, 1, 1]], dtype=np.uint8)
G = np.hstack([np.eye(4, dtype=np.uint8), P])  # 4 x 7 generator matrix
H = np.hstack([P.T, np.eye(3, dtype=np.uint8)])  # 3 x 7 parity-check matrix;  G H^T = 0 (mod 2)

# syndrome (as a number 0..7) -> position of the wrong bit (-1 = no error)
_SYN_TO_POS = {int(H[0, j]) * 4 + int(H[1, j]) * 2 + int(H[2, j]): j for j in range(7)}


def encoded_length(n_data_bits: int) -> int:
    return 7 * -(-n_data_bits // 4)


def data_capacity(n_code_bits: int) -> int:
    """How many data bits fit in n_code_bits coded bits."""
    return 4 * (n_code_bits // 7)


def encode(bits) -> np.ndarray:
    """Data bits -> codeword bits (padded with zeros to a multiple of 4 data bits)."""
    d = np.asarray(bits, dtype=np.uint8).ravel()
    d = np.concatenate([d, np.zeros((-len(d)) % 4, dtype=np.uint8)]).reshape(-1, 4)
    return (d @ G % 2).astype(int).ravel()


def decode(bits) -> tuple[np.ndarray, int]:
    """Codeword bits -> (data bits, number of corrected bits).  Corrects one wrong bit per 7-bit codeword."""
    r = np.asarray(bits, dtype=np.uint8).ravel()
    r = r[: len(r) // 7 * 7].reshape(-1, 7).copy()
    s = (r @ H.T) % 2
    syn = s[:, 0] * 4 + s[:, 1] * 2 + s[:, 2]
    fixed = 0
    for i in np.flatnonzero(syn):
        r[i, _SYN_TO_POS[int(syn[i])]] ^= 1
        fixed += 1
    return r[:, :4].astype(int).ravel(), fixed
