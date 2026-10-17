"""QIM-on-sigma steganography: hide one bit per b x b block in a singular value of the block.

Interval-parity form used in the report: split the sigma axis into intervals of width delta;
interval index q = floor(sigma / delta); bit = q mod 2.  Embedding moves sigma to the CENTRE of the
nearest interval with the wanted parity, so a drift of up to delta/2 either way still reads back.

Defaults follow the configuration chosen in the pilot (results/pilot_decisions.md):
sigma_1 (k = 0), b = 8, delta = 32 (delta / b = 4, about 40.8 dB).

Layers in this module
  * scalar rules        extract_bit, embed_value
  * block level         embed_bits / extract_bits  (closed-loop check, optional secret key)
  * text level          embed_text / extract_text  (frame = length | CRC | UTF-8 payload)
"""

from __future__ import annotations

import binascii
import hashlib
import warnings
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from . import ecc as ecc_mod

DEFAULT_DELTA = 32.0
DEFAULT_B = 8
DEFAULT_K = 0


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
# Block level with closed-loop verification
# ---------------------------------------------------------------------------
def to_blocks(A: np.ndarray, b: int) -> np.ndarray:
    """Cut an image into its b x b blocks, raster order -> array of shape (n_blocks, b, b)."""
    h, w = A.shape
    return A.reshape(h // b, b, w // b, b).swapaxes(1, 2).reshape(-1, b, b)


def from_blocks(blocks: np.ndarray, shape: tuple[int, int], b: int) -> np.ndarray:
    """Inverse of to_blocks: put (n_blocks, b, b) blocks back into an image of the given shape."""
    h, w = shape
    return blocks.reshape(h // b, w // b, b, b).swapaxes(1, 2).reshape(h, w)


def capacity(shape: tuple[int, int], b: int = 8) -> int:
    """Number of bits an image of this shape can carry (1 bit per b x b block)."""
    return (shape[0] // b) * (shape[1] // b)


@dataclass
class StegoResult:
    image: np.ndarray  # integer-valued float matrix (0..255), same shape as the input
    n_bits: int  # bits we tried to hide
    failed: np.ndarray  # bool mask over the hidden bits: True = no safe sigma found, block left unchanged
    weak: np.ndarray | None = None  # bool mask: read back correctly but closer than `margin` to an interval edge

    @property
    def n_failed(self) -> int:
        return int(self.failed.sum())

    @property
    def n_weak(self) -> int:
        return 0 if self.weak is None else int(self.weak.sum())


KDF_SALT = b"svdmark-stego-v2"  # fixed, public: it only stops precomputed tables shared with other programs
KDF_ITERATIONS = 200_000  # every key guess costs this many SHA-256 rounds (about 0.1-0.2 s in Python)


@lru_cache(maxsize=64)
def _key_seed(key: str) -> int:
    """Secret key (any text) -> 256-bit seed with PBKDF2-HMAC-SHA256.

    The first version used CRC32(key): only 2^32 different seeds, so an attacker could simply try them all in
    hours (results/key_strength.csv).  With 256 bits the attacker has to guess the key itself, and every guess
    costs one slow key derivation.  A short or common key can still be guessed.
    """
    return int.from_bytes(hashlib.pbkdf2_hmac("sha256", key.encode("utf-8"), KDF_SALT, KDF_ITERATIONS), "big")


def _dither(n: int, delta: float, key) -> np.ndarray:
    """Secret per-block offsets u_i in [0, 2*delta) derived from `key` (str, or int used as text); zeros if None.

    With a key the interval grid of every block is shifted by its own u_i, so without the key the
    positions sigma/delta mod 1 look uniform instead of piling up at the interval centres.
    """
    if key is None:
        return np.zeros(n)
    return np.random.default_rng(_key_seed(str(key))).uniform(0.0, 2.0 * delta, n)


def embed_bits(
    A: np.ndarray,
    bits,
    delta: float = DEFAULT_DELTA,
    b: int = DEFAULT_B,
    k: int = DEFAULT_K,
    search: int = 3,
    key=None,
    margin: float = 0.25,
) -> StegoResult:
    """Hide `bits` (one per block, raster order) in sigma_k of each b x b block.

    For every block the nearest interval centres with the right parity are tried in order of
    distance (up to +-`search` intervals away).  A candidate is accepted only after a closed-loop
    check: rebuild the block, round to integers 0..255 and read sigma back exactly as the receiver
    will.  This removes the failure sources seen in the early demo -- sigma_k crossing a
    neighbouring sigma (the receiver's sort would then read the wrong index) and pixel rounding.

    Safety margin.  Reading the right bit is not enough: in blocks clipped at 0 or 255 the rebuilt
    sigma can land right next to an interval edge, and then even JPEG 95 flips it.  So pass 1 accepts
    a candidate only if the read-back sigma is at least `margin` * delta away from both edges of its
    interval (0.25 = inside the central half).  Blocks with no such candidate get, in pass 2, the
    correctly-read candidate with the largest margin and are reported in `weak`.  Blocks where no
    candidate reads back correctly are left unchanged and reported in `failed`.

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
    n = len(bits)

    blocks = to_blocks(A, b).copy()
    done = np.zeros(n, dtype=bool)
    weak = np.zeros(n, dtype=bool)
    if n:
        sel = blocks[:n]  # view: blocks that carry a bit (the first n, raster order)
        U, s, Vt = np.linalg.svd(sel)
        sk = s[:, k]
        u = _dither(n, delta, key)
        q = np.floor((sk - u) / delta)[:, None] + np.arange(-search, search + 1)
        centre = u[:, None] + (q + 0.5) * delta
        valid = (centre > 0) & (q % 2 == bits[:, None])
        dist = np.where(valid, np.abs(centre - sk[:, None]), np.inf)
        order = np.argsort(dist, axis=1, kind="stable")
        best_blk = sel.copy()  # pass-2 fallback: correct read with the largest margin
        best_mg = np.full(n, -1.0)
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
            s_read = np.linalg.svd(blk, compute_uv=False)[:, k]
            read = extract_bit_array(s_read, delta, u[pend])
            pos = ((s_read - u[pend]) / delta) % 1.0
            mg = np.minimum(pos, 1.0 - pos)  # distance to the nearer interval edge, in units of delta
            right = ok_cand & (read == bits[pend])
            better = right & (mg > best_mg[pend])
            best_blk[pend[better]] = blk[better]
            best_mg[pend[better]] = mg[better]
            good = right & (mg >= margin)
            sel[pend[good]] = blk[good]
            done[pend[good]] = True
        rest = np.flatnonzero(~done & (best_mg >= 0))  # pass 2
        sel[rest] = best_blk[rest]
        weak[rest] = True
        done[rest] = True
    return StegoResult(from_blocks(blocks, A.shape, b), n, ~done, weak)


def extract_bit_array(sigma, delta: float, offset=0.0):
    """Vectorised extract_bit; `offset` is the (optional) secret grid shift of each value."""
    return (np.floor((np.asarray(sigma, dtype=float) - offset) / delta) % 2).astype(int)


def extract_bits(
    A: np.ndarray, n_bits: int, delta: float = DEFAULT_DELTA, b: int = DEFAULT_B, k: int = DEFAULT_K, key=None
) -> np.ndarray:
    """Read n_bits bits from sigma_k of the first n_bits b x b blocks (raster order)."""
    A = np.asarray(A, dtype=float)
    if A.shape[0] % b or A.shape[1] % b:
        raise ValueError(f"image {A.shape[1]}x{A.shape[0]} is not a multiple of the block size {b}")
    if n_bits > capacity(A.shape, b):
        raise ValueError("n_bits exceeds the image capacity")
    if n_bits == 0:
        return np.zeros(0, dtype=int)
    sig = np.linalg.svd(to_blocks(A, b)[:n_bits], compute_uv=False)
    return extract_bit_array(sig[:, k], delta, _dither(n_bits, delta, key))


# ---------------------------------------------------------------------------
# Text <-> bits.  Frame = 16-bit length (bytes) | 16-bit CRC | UTF-8 payload
#
# The CRC covers the length field AND the payload and starts from 0xFFFF.  With a CRC starting from
# 0 over the payload only, an all-zero header (length 0, CRC 0) is "valid" -- and flat photo blocks
# often read as all-zero bits, so a never-used image used to report status 'ok' with an empty text.
# A message must be at least 1 byte, so length 0 always means "no message".
# ---------------------------------------------------------------------------
HEADER_BITS = 32
CRC_INIT = 0xFFFF


def bytes_to_bits(data: bytes) -> np.ndarray:
    """b'\x05' -> [0 0 0 0 0 1 0 1] (most significant bit first)."""
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8)).astype(int)


def bits_to_bytes(bits) -> bytes:
    """Inverse of bytes_to_bits; a trailing group of fewer than 8 bits is dropped."""
    bits = np.asarray(bits, dtype=np.uint8)
    bits = bits[: len(bits) // 8 * 8]
    return np.packbits(bits).tobytes()


def _crc(length_field: bytes, payload: bytes) -> int:
    return binascii.crc_hqx(length_field + payload, CRC_INIT)


def text_to_bits(text: str) -> np.ndarray:
    payload = text.encode("utf-8")
    if not payload:
        raise ValueError("message is empty: nothing to hide")
    if len(payload) > 0xFFFF:
        raise ValueError("message longer than 65535 bytes")
    length_field = len(payload).to_bytes(2, "big")
    return bytes_to_bits(length_field + _crc(length_field, payload).to_bytes(2, "big") + payload)


def message_bits_needed(text: str, ecc: bool = False) -> int:
    n = HEADER_BITS + 8 * len(text.encode("utf-8"))
    return ecc_mod.encoded_length(n) if ecc else n


def text_capacity_bytes(shape, b: int = DEFAULT_B, ecc: bool = False) -> int:
    """Longest message (UTF-8 bytes) that fits in an image of this shape."""
    cap = capacity(shape, b)
    data = ecc_mod.data_capacity(cap) if ecc else cap
    return max(data - HEADER_BITS, 0) // 8


def bits_to_text(bits) -> tuple[str | None, str]:
    """Decode a frame.  Returns (text, status).

    status  'ok'          length plausible and CRC matches -> text is exactly what was hidden
            'no_message'  the header does not describe a message that fits (length 0 or too long);
                          typical for an image that never carried a message, or a wrong key
            'damaged'     length fits but the CRC does not match (attack, or a wrong key by chance)
    """
    bits = np.asarray(bits)
    if len(bits) < HEADER_BITS:
        return None, "no_message"
    head = bits_to_bytes(bits[:HEADER_BITS])
    length, crc = int.from_bytes(head[:2], "big"), int.from_bytes(head[2:], "big")
    if length == 0 or HEADER_BITS + 8 * length > len(bits):
        return None, "no_message"
    payload = bits_to_bytes(bits[HEADER_BITS : HEADER_BITS + 8 * length])
    if _crc(head[:2], payload) != crc:
        return None, "damaged"
    try:
        return payload.decode("utf-8"), "ok"
    except UnicodeDecodeError:
        return None, "damaged"


def embed_text(
    A: np.ndarray,
    text: str,
    delta: float = DEFAULT_DELTA,
    b: int = DEFAULT_B,
    k: int = DEFAULT_K,
    key=None,
    ecc: bool = False,
) -> StegoResult:
    """Hide a text message.  Raises ValueError with a readable reason if it is empty or does not fit.

    ecc=True protects the frame with Hamming(7,4) (one wrong bit per 7 is corrected); capacity drops to 4/7.
    The coded bits stay in raster order: spreading them over the image was tried and made things worse
    (a cut-out region then hits the message wherever it is, and its errors are too dense to correct anyway,
    while noise / JPEG errors are already independent from block to block).  The receiver must use the same setting.
    If some blocks could not carry their bit safely (see `embed_bits`) a RuntimeWarning is issued.
    """
    frame = text_to_bits(text)
    bits = ecc_mod.encode(frame) if ecc else frame
    cap = capacity(np.shape(A), b)
    if len(bits) > cap:
        raise ValueError(
            f"message needs {len(bits)} bits but this image holds {cap} bits at b={b}"
            f"{' with error correction' if ecc else ''} "
            f"(about {text_capacity_bytes(np.shape(A), b, ecc)} bytes)"
        )
    res = embed_bits(A, bits, delta, b, k, key=key)
    if res.n_failed:
        warnings.warn(
            f"{res.n_failed} of {res.n_bits} blocks could not carry their bit; "
            f"the message may read back as 'damaged' (try k=0 or a larger delta)",
            RuntimeWarning,
            stacklevel=2,
        )
    return res


def extract_text(
    A: np.ndarray,
    delta: float = DEFAULT_DELTA,
    b: int = DEFAULT_B,
    k: int = DEFAULT_K,
    key=None,
    ecc: bool = False,
    details: bool = False,
):
    """Read the header first, then exactly the payload.  See bits_to_text for the status.

    Returns (text, status); with details=True returns (text, status, corrected) where `corrected` is the number
    of bits Hamming(7,4) fixed (always 0 without ecc).
    """
    A = np.asarray(A, dtype=float)
    cap = capacity(A.shape, b)
    fixed = 0

    def read(n_frame_bits):
        nonlocal fixed
        if not ecc:
            return extract_bits(A, n_frame_bits, delta, b, k, key)
        n_code = ecc_mod.encoded_length(n_frame_bits)
        data, fixed = ecc_mod.decode(extract_bits(A, n_code, delta, b, k, key))
        return data[:n_frame_bits]

    def done(text, status):
        return (text, status, fixed) if details else (text, status)

    limit = ecc_mod.data_capacity(cap) if ecc else cap
    if limit < HEADER_BITS:
        return done(None, "no_message")
    head = bits_to_bytes(read(HEADER_BITS))
    length = int.from_bytes(head[:2], "big")
    total = HEADER_BITS + 8 * length
    if length == 0 or total > limit:
        return done(None, "no_message")
    return done(*bits_to_text(read(total)))
