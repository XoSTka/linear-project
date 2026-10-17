"""How hard is it to guess the secret key?  Old seed (CRC32 of the key) vs new seed (PBKDF2-HMAC-SHA256).

The attacker knows the method (it is in the report), the block size and delta, but not the key.  For every
candidate key he rebuilds the per-block grid offsets, reads the 32-bit header and keeps the candidate if the
header describes a message that fits and the CRC matches.

* Old scheme: seed = CRC32(key) -> only 2^32 different grids, whatever the key.  The attacker does not even need
  to guess the key: he can loop over all 2^32 seeds directly.  We time that loop and extrapolate.
* New scheme: seed = PBKDF2-HMAC-SHA256(key, salt, 200 000 iterations) -> 256-bit seed; looping over seeds is
  impossible (2^256), so the attacker must guess keys, and every guess costs one PBKDF2 run.  We time that.
* Dictionary attack: a list of common words with the real key in it -- still found, only slower.
  So the key must still be a real password, not "1234".

Output: results/key_strength.csv
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd

from svdmark import stego
from svdmark.data import eval_set, list_images, load_gray

ROOT = Path(__file__).resolve().parents[1]

B, DELTA = 8, 32.0
TEXT, KEY = "นัดบ่ายสาม ตึก 12", "kmitl"


def legacy_dither(n, delta, seed):
    return np.random.default_rng(seed).uniform(0.0, 2.0 * delta, n)


def header_ok(sig, offsets, cap):
    """Do the 32 header bits read with these grid offsets describe a message that fits?"""
    head = stego.bits_to_bytes(stego.extract_bit_array(sig, DELTA, offsets))
    length = int.from_bytes(head[:2], "big")
    return 0 < length and stego.HEADER_BITS + 8 * length <= cap


A = load_gray(eval_set(list_images(ROOT / "data" / "images"))["path"].iloc[0])
cap = stego.capacity(A.shape, B)
r = stego.embed_text(A, TEXT, DELTA, B, key=KEY)
sig32 = np.linalg.svd(stego.to_blocks(r.image, B)[: stego.HEADER_BITS], compute_uv=False)[:, 0]
rows = []

# --- old scheme: loop over seeds (the attacker's best strategy)
N = 20000
t0 = time.perf_counter()
hits = 0
for seed in range(N):
    hits += header_ok(sig32, legacy_dither(32, DELTA, seed), cap)
dt = time.perf_counter() - t0
rate_old = N / dt
rows.append(dict(scheme="old: seed = CRC32(key)", what="seeds tried per second (one core)", value=rate_old))
rows.append(
    dict(scheme="old: seed = CRC32(key)", what="false header candidates per 20000 seeds (need CRC check)", value=hits)
)
rows.append(
    dict(scheme="old: seed = CRC32(key)", what="hours to try all 2^32 seeds (one core)", value=2**32 / rate_old / 3600)
)
rows.append(
    dict(
        scheme="old: seed = CRC32(key)", what="hours to try all 2^32 seeds (8 cores)", value=2**32 / rate_old / 3600 / 8
    )
)

# --- new scheme: every guess costs one key derivation
t0 = time.perf_counter()
M = 10
for i in range(M):
    stego._key_seed.__wrapped__(f"guess{i}")  # __wrapped__ skips the lru_cache, so every call really derives the key
t_kdf = (time.perf_counter() - t0) / M
rows.append(dict(scheme="new: seed = PBKDF2-HMAC-SHA256", what="seconds per key guess (one core)", value=t_kdf))
rows.append(dict(scheme="new: seed = PBKDF2-HMAC-SHA256", what="different seeds possible (log2)", value=256))
for name, space in [("8 random lowercase letters", 26**8), ("10 random letters+digits", 62**10)]:
    rows.append(
        dict(
            scheme="new: seed = PBKDF2-HMAC-SHA256",
            what=f"years to try every {name} (8 cores)",
            value=space * t_kdf / 8 / 3600 / 24 / 365,
        )
    )

# --- dictionary attack on the real key: still works if the key is a common word (new scheme, measured)
common = [f"pass{i}" for i in range(49)] + [KEY]
t0 = time.perf_counter()
found = next((w for w in common if stego.extract_text(r.image, DELTA, B, key=w)[1] == "ok"), None)
t_dict = time.perf_counter() - t0
rows.append(
    dict(
        scheme="new: seed = PBKDF2-HMAC-SHA256",
        what=f"seconds to find the key '{found}' in a {len(common)}-word list",
        value=t_dict,
    )
)

out = pd.DataFrame(rows)
out.to_csv(ROOT / "results" / "key_strength.csv", index=False, float_format="%.6g")
pd.set_option("display.width", 200)
print(out.to_string(index=False))
