from pathlib import Path

import numpy as np
import pytest

from svdmark import metrics, watermark
from svdmark.data import eval_set, list_images, load_gray

ROOT = Path(__file__).resolve().parents[1]


def synth(h=64, w=96, seed=0):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    return np.clip(np.rint(110 + 50 * np.sin(x / 8) + 30 * np.cos(y / 6) + rng.normal(0, 5, (h, w))), 0, 255)


def test_rectangular_image_uses_min_side_watermark():
    A = synth(64, 96)
    W = np.random.default_rng(1).integers(0, 2, (64, 64)).astype(float)
    Aw, key = watermark.embed(A, W, alpha=8)
    assert Aw.shape == A.shape
    assert watermark.extract(Aw, key) == pytest.approx(W, abs=1e-8)


def test_wrong_watermark_shape_rejected():
    with pytest.raises(ValueError):
        watermark.embed(synth(64, 96), np.zeros((96, 96)), alpha=8)


def test_frobenius_identity_on_rectangular_image():
    A = synth(64, 96)
    W = np.random.default_rng(2).integers(0, 2, (64, 64)).astype(float)
    Aw, key = watermark.embed(A, W, alpha=8)
    sw = np.linalg.svd(Aw, compute_uv=False)
    assert np.linalg.norm(Aw - A) == pytest.approx(np.linalg.norm(sw - key.S), rel=1e-9)


@pytest.mark.skipif(not list(ROOT.glob("data/images/*/*.jpg")), reason="dataset not downloaded")
def test_real_image_uint8_round_trip():
    A = load_gray(eval_set(list_images(ROOT / "data" / "images"))["path"].iloc[0])
    k = min(A.shape)
    W = np.random.default_rng(7).integers(0, 2, (k, k)).astype(float)
    Aw, key = watermark.embed(A, W, alpha=8)
    Au = np.clip(np.rint(Aw), 0, 255)  # saved as an 8-bit image
    W_star = watermark.extract(Au, key)
    assert metrics.psnr(A, Au) > 40
    assert metrics.ncc(W, W_star) > 0.99
    assert metrics.ber(W, W_star > 0.5) < 0.01


def test_shift_score_separates_marked_from_unmarked():
    A = synth(64, 96)
    W = np.random.default_rng(3).integers(0, 2, (64, 64)).astype(float)
    Aw, key = watermark.embed(A, W, alpha=16)
    assert watermark.shift_score(Aw, key) == pytest.approx(1.0, abs=1e-9)
    assert watermark.shift_score(A, key) == 0.0  # untouched original: nothing moved
    # while plain NCC on the unmarked original is far above chance (the false positive we report;
    # on the 320x480 photos it is 0.96-0.98, see results/pilot_decisions.md)
    assert metrics.ncc(W, watermark.extract(A, key)) > 0.5
