"""QIM-on-sigma steganography (scalar building blocks).

Interval-parity form used in the report: split the sigma axis into intervals of
width delta; interval index q = floor(sigma / delta); bit = q mod 2.  Embedding
moves sigma to the CENTRE of the nearest interval with the wanted parity, so a
drift of up to delta/2 in either direction still reads back correctly.

(The block-level embed/extract with the closed-loop check is added in the next step.)
"""
from __future__ import annotations

import numpy as np


def extract_bit(sigma: float, delta: float) -> int:
    """Bit carried by sigma: parity of the interval floor(sigma/delta)."""
    return int(np.floor(sigma / delta)) % 2


def embed_value(sigma: float, bit: int, delta: float) -> float:
    """Centre of the nearest interval whose parity equals `bit`."""
    q = int(np.floor(sigma / delta))
    if q % 2 != bit:
        # neighbour intervals are q-1 and q+1; pick the nearer centre (never below 0)
        up, down = q + 1, q - 1
        if down < 0 or abs((up + 0.5) * delta - sigma) <= abs((down + 0.5) * delta - sigma):
            q = up
        else:
            q = down
    return (q + 0.5) * delta


# ---------------------------------------------------------------------------
# Block-level embedding with closed-loop verification
# ---------------------------------------------------------------------------
import binascii
from dataclasses import dataclass


def _to_blocks(A: np.ndarray, b: int) -> np.ndarray:
    h, w = A.shape
    return A.reshape(h // b, b, w // b, b).swapaxes(1, 2).reshape(-1, b, b)


def _from_blocks(blocks: np.ndarray, shape: tuple[int, int], b: int) -> np.ndarray:
    h, w = shape
    return blocks.reshape(h // b, w // b, b, b).swapaxes(1, 2).reshape(h, w)


def capacity(shape: tuple[int, int], b: int = 8) -> int:
    """Number of bits an image of this shape can carry (1 bit per b x b block)."""
    return (shape[0] // b) * (shape[1] // b)


@dataclass
class StegoResult:
    image: np.ndarray        # integer-valued float matrix (0..255), same shape as the input
    n_bits: int              # bits we tried to hide
    failed: np.ndarray       # bool mask over the hidden bits: True = no safe sigma found, block left unchanged

    @property
    def n_failed(self) -> int:
        return int(self.failed.sum())


def _dither(n: int, delta: float, key) -> np.ndarray:
    """Secret per-block offsets u_i in [0, 2*delta) derived from `key` (int or str); zeros if key is None.

    With a key the interval grid of every block is shifted by its own u_i, so without the key the
    positions sigma/delta mod 1 look uniform instead of piling up at the interval centres.
    """
    if key is None:
        return np.zeros(n)
    seed = binascii.crc32(key.encode("utf-8")) if isinstance(key, str) else int(key)
    return np.random.default_rng(seed).uniform(0.0, 2.0 * delta, n)


def embed_bits(A: np.ndarray, bits, delta: float = 16.0, b: int = 8, k: int = 1,
               search: int = 3, key=None) -> StegoResult:
    """Hide `bits` (one per block, raster order) in sigma_k of each b x b block.

    For every block the nearest interval centres with the right parity are tried in
    order of distance (up to +-`search` intervals away).  A candidate is accepted only
    after a closed-loop check: rebuild the block, round to integers 0..255 and read
    the bit back exactly as the receiver will.  This removes the two failure sources
    seen in the demo -- sigma_k crossing a neighbouring sigma (the receiver's sort
    would then read the wrong index) and pixel rounding.  Blocks where no candidate
    survives are left unchanged and reported in `failed`.

    `key` (optional int or str) shifts each block's interval grid by a secret offset (see `_dither`);
    the same key must be given to `extract_bits`.  Without a key the grid is the plain one.
    """
    A = np.asarray(A, dtype=float)
    bits = np.asarray(bits, dtype=int).ravel()
    h, w = A.shape
    if h % b or w % b:
        raise ValueError(f"image {w}x{h} is not a multiple of the block size {b}")
    if not 0 <= k < b:
        raise ValueError(f"k must be in [0, {b - 1}]")
    if len(bits) > capacity(A.shape, b):
        raise ValueError(f"{len(bits)} bits do not fit: capacity is {capacity(A.shape, b)} bits")

    blocks = _to_blocks(A, b).copy()
    n = len(bits)
    done = np.zeros(n, dtype=bool)
    if n:
        sel = blocks[:n]
        U, s, Vt = np.linalg.svd(sel)
        sk = s[:, k]
        u = _dither(n, delta, key)
        q = np.floor((sk - u) / delta)[:, None] + np.arange(-search, search + 1)
        centre = u[:, None] + (q + 0.5) * delta
        valid = (centre > 0) & (q % 2 == bits[:, None])
        dist = np.where(valid, np.abs(centre - sk[:, None]), np.inf)
        order = np.argsort(dist, axis=1, kind="stable")
        for j in range(order.shape[1]):
            pend = np.flatnonzero(~done)
            if pend.size == 0:
                break
            col = order[pend, j]
            ok_cand = np.isfinite(dist[pend, col])
            if not ok_cand.any():
                continue
            s_new = s[pend].copy()
            s_new[:, k] = np.where(ok_cand, centre[pend, col], s_new[:, k])
            blk = np.clip(np.rint((U[pend] * s_new[:, None, :]) @ Vt[pend]), 0, 255)
            read = extract_bit_array(np.linalg.svd(blk, compute_uv=False)[:, k], delta, u[pend])
            good = ok_cand & (read == bits[pend])
            sel[pend[good]] = blk[good]
            done[pend[good]] = True
        blocks[:n] = sel
    return StegoResult(_from_blocks(blocks, A.shape, b), n, ~done)


def extract_bit_array(sigma, delta: float, offset=0.0):
    """Vectorised extract_bit; `offset` is the (optional) secret grid shift of each value."""
    return (np.floor((np.asarray(sigma, dtype=float) - offset) / delta) % 2).astype(int)


def extract_bits(A: np.ndarray, n_bits: int, delta: float = 16.0, b: int = 8, k: int = 1, key=None) -> np.ndarray:
    """Read the first n_bits bits from sigma_k of the b x b blocks (raster order)."""
    A = np.asarray(A, dtype=float)
    if A.shape[0] % b or A.shape[1] % b:
        raise ValueError(f"image {A.shape[1]}x{A.shape[0]} is not a multiple of the block size {b}")
    if n_bits > capacity(A.shape, b):
        raise ValueError("n_bits exceeds the image capacity")
    sig = np.linalg.svd(_to_blocks(A, b)[:n_bits], compute_uv=False)
    return extract_bit_array(sig[:, k], delta, _dither(n_bits, delta, key))


# ---------------------------------------------------------------------------
# Text <-> bits.  Frame = 16-bit length (bytes) | 16-bit CRC | UTF-8 payload
# ---------------------------------------------------------------------------
HEADER_BITS = 32


def _bytes_to_bits(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8)).astype(int)


def _bits_to_bytes(bits) -> bytes:
    bits = np.asarray(bits, dtype=np.uint8)
    bits = bits[: len(bits) // 8 * 8]
    return np.packbits(bits).tobytes()


def text_to_bits(text: str) -> np.ndarray:
    payload = text.encode("utf-8")
    if len(payload) > 0xFFFF:
        raise ValueError("message longer than 65535 bytes")
    head = len(payload).to_bytes(2, "big") + binascii.crc_hqx(payload, 0).to_bytes(2, "big")
    return _bytes_to_bits(head + payload)


def message_bits_needed(text: str) -> int:
    return HEADER_BITS + 8 * len(text.encode("utf-8"))


def bits_to_text(bits) -> tuple[str | None, str]:
    """Decode a frame.  Returns (text, status); status is 'ok', 'no_message' or 'damaged'."""
    bits = np.asarray(bits)
    if len(bits) < HEADER_BITS:
        return None, "no_message"
    head = _bits_to_bytes(bits[:HEADER_BITS])
    length, crc = int.from_bytes(head[:2], "big"), int.from_bytes(head[2:], "big")
    if HEADER_BITS + 8 * length > len(bits):
        return None, "no_message"
    payload = _bits_to_bytes(bits[HEADER_BITS:HEADER_BITS + 8 * length])
    if binascii.crc_hqx(payload, 0) != crc:
        return None, "damaged"
    try:
        return payload.decode("utf-8"), "ok"
    except UnicodeDecodeError:
        return None, "damaged"


def embed_text(A: np.ndarray, text: str, delta: float = 16.0, b: int = 8, k: int = 1, key=None) -> StegoResult:
    """Hide a text message.  Raises ValueError with a readable reason if it does not fit."""
    need, cap = message_bits_needed(text), capacity(np.shape(A), b)
    if need > cap:
        raise ValueError(f"message needs {need} bits but this image holds {cap} bits at b={b} "
                         f"(about {max(cap - HEADER_BITS, 0) // 8} bytes)")
    return embed_bits(A, text_to_bits(text), delta, b, k, key=key)


def extract_text(A: np.ndarray, delta: float = 16.0, b: int = 8, k: int = 1, key=None) -> tuple[str | None, str]:
    """Read the header first, then exactly the payload.  See bits_to_text for the status."""
    A = np.asarray(A, dtype=float)
    cap = capacity(A.shape, b)
    if cap < HEADER_BITS:
        return None, "no_message"
    head = _bits_to_bytes(extract_bits(A, HEADER_BITS, delta, b, k, key))
    length = int.from_bytes(head[:2], "big")
    total = HEADER_BITS + 8 * length
    if total > cap:
        return None, "no_message"
    return bits_to_text(extract_bits(A, total, delta, b, k, key))
