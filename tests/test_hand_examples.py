"""Check the three hand-calculation examples from the report against code.

Tolerance 1e-3 as in the report.  Example 2 uses the same A as Example 1
(the report's part-1 file with the exact noise matrix E is not in this repo,
so the noisy case is checked as a property: small E -> NCC > 0.99, BER = 0).
"""
import numpy as np
import pytest

from svdmark import metrics, stego, watermark
from svdmark.svd_utils import energy, reconstruct, svd, svd_2x2_by_hand

TOL = 1e-3


# ---------- Example 1: SVD of A = [[3,0],[4,5]] ----------
A1 = np.array([[3.0, 0.0], [4.0, 5.0]])


def test_ex1_singular_values_closed_form():
    _, s, _ = svd(A1)
    assert s[0] == pytest.approx(3 * np.sqrt(5), abs=TOL)   # 6.7082
    assert s[1] == pytest.approx(np.sqrt(5), abs=TOL)       # 2.2361


def test_ex1_energy_equals_frobenius_norm_squared():
    _, s, _ = svd(A1)
    assert energy(s) == pytest.approx(50.0, abs=TOL)
    assert np.linalg.norm(A1, "fro") ** 2 == pytest.approx(50.0, abs=TOL)


def test_ex1_by_hand_matches_numpy():
    U, s, Vt = svd_2x2_by_hand(A1)
    assert s == pytest.approx(svd(A1)[1], abs=1e-9)
    assert reconstruct(U, s, Vt) == pytest.approx(A1, abs=1e-9)
    assert U.T @ U == pytest.approx(np.eye(2), abs=1e-9)
    assert Vt @ Vt.T == pytest.approx(np.eye(2), abs=1e-9)


@pytest.mark.parametrize("M", [np.diag([5.0, 2.0]), np.array([[2.0, 2.0], [1.0, 1.0]]),
                               np.array([[0.0, 1.0], [1.0, 0.0]]), np.zeros((2, 2))])
def test_by_hand_edge_cases(M):
    U, s, Vt = svd_2x2_by_hand(M)
    assert reconstruct(U, s, Vt) == pytest.approx(M, abs=1e-9)


# ---------- Example 2: Liu-Tan embed / extract, W = [[1,0],[1,1]], alpha = 0.5 ----------
W2 = np.array([[1.0, 0.0], [1.0, 1.0]])


def test_ex2_no_attack_recovers_W_exactly():
    Aw, key = watermark.embed(A1, W2, alpha=0.5)
    W_star = watermark.extract(Aw, key)
    assert W_star == pytest.approx(W2, abs=TOL)
    assert metrics.ncc(W2, W_star) == pytest.approx(1.0, abs=TOL)


def test_ex2_embedding_changes_sigma_not_the_bases():
    # ||Aw - A||_F == ||Sw - S||_F because U, V are orthogonal
    Aw, key = watermark.embed(A1, W2, alpha=0.5)
    sw = np.linalg.svd(Aw, compute_uv=False)
    assert np.linalg.norm(Aw - A1) == pytest.approx(np.linalg.norm(sw - key.S), abs=1e-9)


def test_ex2_small_noise_still_extracts():
    Aw, key = watermark.embed(A1, W2, alpha=0.5)
    E = 0.1 * np.array([[1.0, -1.0], [1.0, 1.0]])           # small perturbation
    W_star = watermark.extract(Aw + E, key)
    assert metrics.ncc(W2, W_star) > 0.99
    assert metrics.ber(W2, (W_star > 0.5).astype(int)) == 0.0


# ---------- Example 3: hide a bit in the 2x2 block [[52,55],[61,59]], delta = 6 ----------
B3 = np.array([[52.0, 55.0], [61.0, 59.0]])
DELTA = 6.0


def test_ex3_embed_sigma1_to_117_and_extract_bit_1():
    U, s, Vt = svd(B3)
    assert stego.extract_bit(s[0], DELTA) == 0               # sigma1 = 113.69 sits in interval 18 (even)
    s_new = s.copy()
    s_new[0] = stego.embed_value(s[0], bit=1, delta=DELTA)
    assert s_new[0] == pytest.approx(117.0, abs=TOL)         # centre of interval 19
    Bw = np.rint(reconstruct(U, s_new, Vt))                  # back to integer pixels
    sigma_read = np.linalg.svd(Bw, compute_uv=False)[0]
    assert stego.extract_bit(sigma_read, DELTA) == 1         # closed-loop read-back
    assert metrics.psnr(B3, Bw) == pytest.approx(42.11, abs=0.01)


def test_qim_interval_parity_vs_rounding():
    # delta = 10, sigma = 37: interval 3 (odd) -> bit 1.  A rounding-based rule
    # (round(3.7) = 4) would wrongly say 0, which is the "wrong formula" case.
    assert stego.extract_bit(37.0, 10.0) == 1
    assert int(np.rint(37.0 / 10.0)) % 2 == 0


@pytest.mark.parametrize("sigma", [0.4, 5.9, 6.0, 37.0, 113.69, 1000.3])
@pytest.mark.parametrize("bit", [0, 1])
def test_embed_value_round_trip_and_max_move(sigma, bit):
    new = stego.embed_value(sigma, bit, DELTA)
    assert stego.extract_bit(new, DELTA) == bit
    # moves at most delta, except in the lowest interval (sigma < delta) where
    # only the upper neighbour exists and the move can reach 1.5 delta
    limit = 1.5 * DELTA if sigma < DELTA else DELTA
    assert abs(new - sigma) <= limit + 1e-9
    assert new >= 0
