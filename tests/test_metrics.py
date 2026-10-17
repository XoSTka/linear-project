"""Metrics with small hand-checkable inputs."""

import numpy as np
import pandas as pd
import pytest

from svdmark.metrics import auc, ber, ncc, ncc_centered, psnr


def test_psnr_hand_value():
    a = np.zeros((2, 2))
    b = np.array([[0, 0], [0, 2.0]])  # MSE = 4 / 4 = 1  ->  PSNR = 10 log10(255^2)
    assert psnr(a, b) == pytest.approx(20 * np.log10(255))
    assert psnr(a, a) == float("inf")


def test_ber_and_ncc():
    assert ber([0, 1, 1, 0], [0, 1, 0, 0]) == 0.25
    assert ncc([1, 0], [2, 0]) == pytest.approx(1.0)
    assert ncc([0, 0], [1, 1]) == 0.0  # zero vector: defined as 0, not a division error


def test_ncc_centered_removes_the_all_positive_bias():
    rng = np.random.default_rng(0)
    w, other = rng.integers(0, 2, (64, 64)), rng.integers(0, 2, (64, 64))
    assert ncc(w, other) == pytest.approx(0.5, abs=0.05)  # unrelated 0/1 marks still look half-similar
    assert abs(ncc_centered(w, other)) < 0.05  # ... until the means are removed
    assert ncc_centered(w, w) == pytest.approx(1.0)


def test_auc_hand_examples():
    assert auc([3, 4], [1, 2]) == 1.0  # every positive above every negative
    assert auc([1, 2], [3, 4]) == 0.0
    assert auc([2], [1, 2, 3]) == pytest.approx((1 + 0.5) / 3)  # one below, one tie (1/2), one above


def test_auc_equals_rank_formula():
    """The rank (Mann-Whitney) formula the experiment scripts used before, ties given average ranks."""
    rng = np.random.default_rng(1)
    pos, neg = rng.integers(0, 20, 300).astype(float), rng.integers(0, 20, 500).astype(float)
    ranks = pd.Series(np.concatenate([pos, neg])).rank().to_numpy()
    expected = (ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))
    assert auc(pos, neg) == expected
