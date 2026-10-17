"""Hamming(7,4): the matrix facts from the report, and single-error correction."""

import itertools

import numpy as np
import pytest

from svdmark import ecc, stego


def test_generator_and_parity_check_are_orthogonal():
    assert not ((ecc.G @ ecc.H.T) % 2).any()  # G H^T = 0 (mod 2): every codeword has syndrome 0


def test_columns_of_H_are_distinct_and_nonzero():
    cols = {tuple(c) for c in ecc.H.T}
    assert len(cols) == 7 and (0, 0, 0) not in cols


def test_all_16_messages_and_all_single_errors_are_corrected():
    for d in itertools.product([0, 1], repeat=4):
        c = ecc.encode(d)
        assert list(ecc.decode(c)[0]) == list(d)
        for j in range(7):
            r = c.copy()
            r[j] ^= 1
            got, fixed = ecc.decode(r)
            assert list(got) == list(d) and fixed == 1


def test_lengths():
    assert ecc.encoded_length(32) == 56 and ecc.encoded_length(33) == 63
    assert ecc.data_capacity(2400) == 1368


@pytest.mark.parametrize("b, delta", [(8, 32.0), (16, 64.0)])
def test_text_round_trip_with_ecc(b, delta):
    rng = np.random.default_rng(1)
    y, x = np.mgrid[0:256, 0:384]
    A = np.clip(np.rint(100 + 50 * np.sin(x / 9) + 30 * np.cos(y / 7) + rng.normal(0, 4, x.shape)), 0, 255)
    r = stego.embed_text(A, "hi สวัสดี", delta, b, key="k", ecc=True)
    assert stego.extract_text(r.image, delta, b, key="k", ecc=True) == ("hi สวัสดี", "ok")
    assert stego.extract_text(r.image, delta, b, key="k", ecc=False)[1] != "ok"  # settings must match


def test_ecc_capacity_message():
    assert stego.text_capacity_bytes((320, 480), 8, ecc=True) == 167
    assert stego.text_capacity_bytes((320, 480), 8, ecc=False) == 296
