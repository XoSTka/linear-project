import numpy as np
import pytest

from svdmark import attacks
from svdmark.metrics import psnr


def img(seed=0):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:64, 0:96]
    return np.clip(np.rint(110 + 50 * np.sin(x / 8) + 30 * np.cos(y / 6) + rng.normal(0, 5, (64, 96))), 0, 255)


@pytest.mark.parametrize("name,level", list(attacks.all_attacks()))
def test_output_is_8bit_like_same_shape(name, level):
    out = attacks.apply(name, img(), level)
    assert out.shape == (64, 96)
    assert out.min() >= 0 and out.max() <= 255 and np.all(out == np.rint(out))


def test_none_is_identity_for_integer_image():
    assert np.array_equal(attacks.apply("none", img()), img())


def test_noise_is_seeded_and_psnr_matches_std():
    a = img()
    assert np.array_equal(attacks.gaussian_noise(a, 4, seed=1), attacks.gaussian_noise(a, 4, seed=1))
    assert not np.array_equal(attacks.gaussian_noise(a, 4, seed=1), attacks.gaussian_noise(a, 4, seed=2))
    assert psnr(a, attacks.gaussian_noise(a, 4, seed=1)) == pytest.approx(10 * np.log10(255**2 / 16), abs=1.0)


def test_jpeg_worse_with_lower_quality():
    a = img()
    p = [psnr(a, attacks.jpeg(a, q)) for q in attacks.LEVELS["jpeg"]]
    assert p == sorted(p, reverse=True)


def test_crop_removes_requested_area():
    a = np.full((320, 480), 200.0)
    out = attacks.crop_out(a, 0.25)
    assert (out == 0).mean() == pytest.approx(0.25, abs=0.01)
    assert out[0, 0] == 200 and out[160, 240] == 0  # border kept, centre removed


def test_label_matches_result_table_names():
    assert attacks.label("none") == "none"
    assert attacks.label("jpeg", 75) == "jpeg75"
    assert attacks.label("crop", 0.10) == "crop0.1"
    assert [attacks.label(n, lv) for n, lv in attacks.all_attacks()][:3] == ["none", "noise1", "noise2"]
