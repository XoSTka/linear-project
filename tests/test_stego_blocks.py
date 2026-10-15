from pathlib import Path

import numpy as np
import pytest

from svdmark import stego
from svdmark.data import list_images, load_gray, sample_images
from svdmark.metrics import ber, psnr

ROOT = Path(__file__).resolve().parents[1]


def synthetic(h=64, w=96, seed=0):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    img = 90 + 60 * np.sin(x / 9.0) + 40 * np.cos(y / 7.0) + rng.normal(0, 4, (h, w))
    return np.clip(np.rint(img), 0, 255)


def test_capacity():
    assert stego.capacity((320, 480), 8) == 2400
    assert stego.capacity((320, 480), 4) == 9600


@pytest.mark.parametrize("b", [4, 8, 16])
@pytest.mark.parametrize("delta", [16.0, 32.0])
def test_round_trip_no_attack(b, delta):
    A = synthetic()
    bits = np.random.default_rng(1).integers(0, 2, stego.capacity(A.shape, b))
    r = stego.embed_bits(A, bits, delta, b)
    assert r.image.min() >= 0 and r.image.max() <= 255
    assert np.all(r.image == np.rint(r.image))                    # integer pixels
    got = stego.extract_bits(r.image, len(bits), delta, b)
    # every block the embedder declared safe must read back correctly
    assert np.all(got[~r.failed] == bits[~r.failed])
    assert r.n_failed <= 0.05 * len(bits)


def test_unused_blocks_untouched():
    A = synthetic()
    r = stego.embed_bits(A, np.ones(5, dtype=int), 16.0, 8)
    assert np.array_equal(r.image[8:], A[8:])                     # 5 blocks fit in the first block-row (96/8 = 12 per row)


def test_too_many_bits_rejected():
    with pytest.raises(ValueError):
        stego.embed_bits(synthetic(), np.zeros(10_000, dtype=int), 16.0, 8)


@pytest.mark.parametrize("msg", ["hello", "สวัสดีครับ SVD 123", "", "a" * 30])
def test_text_round_trip(msg):
    A = synthetic(128, 192)
    r = stego.embed_text(A, msg, 16.0, 8)
    text, status = stego.extract_text(r.image, 16.0, 8)
    assert r.n_failed == 0                                        # clean synthetic image: every block is safe
    assert (text, status) == (msg, "ok")


def test_text_too_long_has_readable_error():
    with pytest.raises(ValueError, match="holds"):
        stego.embed_text(synthetic(), "x" * 500, 16.0, 8)


def test_clean_image_reports_no_message():
    assert stego.extract_text(synthetic(), 16.0, 8)[1] in ("no_message", "damaged")


def test_damage_detected_by_crc():
    A = synthetic(128, 192)
    r = stego.embed_text(A, "secret message", 16.0, 8)
    noisy = np.clip(r.image + np.random.default_rng(3).normal(0, 12, A.shape), 0, 255)
    text, status = stego.extract_text(noisy, 16.0, 8)
    # heavy noise must never produce a *wrong* message that looks valid
    assert (status == "ok" and text == "secret message") or (status in ("damaged", "no_message") and text is None)


@pytest.mark.skipif(not list(ROOT.glob("data/images/*/*.jpg")), reason="dataset not downloaded")
def test_real_image_full_capacity():
    df = sample_images(list_images(ROOT / "data" / "images"))
    A = load_gray(df["path"].iloc[0])
    bits = np.random.default_rng(2).integers(0, 2, stego.capacity(A.shape, 8))
    r = stego.embed_bits(A, bits, 16.0, 8)
    got = stego.extract_bits(r.image, len(bits), 16.0, 8)
    assert ber(bits[~r.failed], got[~r.failed]) == 0.0
    assert psnr(A, r.image) > 35


# ---------------- secret key (grid dither) ----------------
@pytest.mark.parametrize("key", [123, "รหัสลับ"])
def test_keyed_round_trip(key):
    A = synthetic(128, 192)
    bits = np.random.default_rng(4).integers(0, 2, stego.capacity(A.shape, 8))
    r = stego.embed_bits(A, bits, 16.0, 8, k=0, key=key)
    got = stego.extract_bits(r.image, len(bits), 16.0, 8, k=0, key=key)
    assert np.all(got[~r.failed] == bits[~r.failed]) and r.n_failed <= 0.05 * len(bits)


def test_wrong_key_reads_noise_and_text_is_refused():
    A = synthetic(128, 192)
    r = stego.embed_text(A, "secret message", 16.0, 8, k=0, key="password")
    assert stego.extract_text(r.image, 16.0, 8, k=0, key="password") == ("secret message", "ok")
    text, status = stego.extract_text(r.image, 16.0, 8, k=0, key="wrong")
    assert text is None and status in ("damaged", "no_message")
    text, status = stego.extract_text(r.image, 16.0, 8, k=0)              # no key at all
    assert text is None


def test_key_none_matches_plain_scheme():
    A = synthetic()
    bits = np.random.default_rng(5).integers(0, 2, 30)
    a = stego.embed_bits(A, bits, 16.0, 8, k=0)
    b_ = stego.embed_bits(A, bits, 16.0, 8, k=0, key=None)
    assert np.array_equal(a.image, b_.image)
