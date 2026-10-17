from pathlib import Path

import numpy as np
import pytest

from svdmark import stego
from svdmark.data import eval_set, list_images, load_gray
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
    assert np.all(r.image == np.rint(r.image))  # integer pixels
    got = stego.extract_bits(r.image, len(bits), delta, b)
    # every block the embedder declared safe must read back correctly
    assert np.all(got[~r.failed] == bits[~r.failed])
    assert r.n_failed <= 0.05 * len(bits)


def test_unused_blocks_untouched():
    A = synthetic()
    r = stego.embed_bits(A, np.ones(5, dtype=int), 16.0, 8)
    assert np.array_equal(r.image[8:], A[8:])  # 5 blocks fit in the first block-row (96/8 = 12 per row)


def test_too_many_bits_rejected():
    with pytest.raises(ValueError):
        stego.embed_bits(synthetic(), np.zeros(10_000, dtype=int), 16.0, 8)


@pytest.mark.parametrize("msg", ["hello", "สวัสดีครับ SVD 123", "a", "a" * 30])
def test_text_round_trip(msg):
    A = synthetic(128, 192)
    r = stego.embed_text(A, msg, 16.0, 8)
    text, status = stego.extract_text(r.image, 16.0, 8)
    assert r.n_failed == 0  # clean synthetic image: every block is safe
    assert (text, status) == (msg, "ok")


def test_text_too_long_has_readable_error():
    with pytest.raises(ValueError, match="holds"):
        stego.embed_text(synthetic(), "x" * 500, 16.0, 8)


def test_empty_message_rejected():
    with pytest.raises(ValueError, match="empty"):
        stego.embed_text(synthetic(128, 192), "")


def test_all_zero_header_is_not_a_message():
    # flat photo blocks read as all-zero bits; that must never decode as a valid (empty) message
    assert stego.bits_to_text(np.zeros(200, dtype=int)) == (None, "no_message")
    one_zero_byte = np.zeros(stego.HEADER_BITS + 8, dtype=int)
    one_zero_byte[15] = 1  # length 1, CRC 0, payload 0x00
    assert stego.bits_to_text(one_zero_byte)[1] != "ok"


def test_defaults_are_the_chosen_configuration():
    assert (stego.DEFAULT_K, stego.DEFAULT_B, stego.DEFAULT_DELTA) == (0, 8, 32.0)


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
    df = eval_set(list_images(ROOT / "data" / "images"))
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
    text, status = stego.extract_text(r.image, 16.0, 8, k=0)  # no key at all
    assert text is None


def test_key_none_matches_plain_scheme():
    A = synthetic()
    bits = np.random.default_rng(5).integers(0, 2, 30)
    a = stego.embed_bits(A, bits, 16.0, 8, k=0)
    b_ = stego.embed_bits(A, bits, 16.0, 8, k=0, key=None)
    assert np.array_equal(a.image, b_.image)


# ---------------- real photos (skipped when the dataset is not downloaded) ----------------
needs_data = pytest.mark.skipif(not list(ROOT.glob("data/images/*/*.jpg")), reason="dataset not downloaded")


@needs_data
@pytest.mark.parametrize("b, delta", [(4, 16.0), (8, 32.0), (16, 64.0)])
def test_never_used_photos_never_report_ok(b, delta):
    df = eval_set(list_images(ROOT / "data" / "images")).iloc[::10]  # 40 photos
    for p in df["path"]:
        text, status = stego.extract_text(load_gray(p), delta, b)
        assert status != "ok", p


@needs_data
def test_real_photos_text_round_trip_and_wrong_key():
    df = eval_set(list_images(ROOT / "data" / "images")).iloc[::40]  # 10 photos
    msg = "ข้อความลับ SVD " * 7  # 245 bytes = 2 kbit of the 2.4 kbit capacity
    for p in df["path"]:
        A = load_gray(p)
        r = stego.embed_text(A, msg, key="password")  # default k=0, b=8, delta=32
        assert r.n_failed == 0
        assert stego.extract_text(r.image, key="password") == (msg, "ok")
        assert stego.extract_text(r.image, key="wrong")[0] is None
        assert stego.extract_text(r.image)[0] is None  # no key


@needs_data
def test_safety_margin_survives_light_jpeg_on_clipped_white_blocks():
    # 196040.jpg has large areas at 255; without the margin rule one block sat at an interval edge
    # and JPEG 95 flipped it (message 'damaged').
    from svdmark import attacks

    hits = list(ROOT.glob("data/images/*/196040.jpg"))
    A = load_gray(hits[0])
    r = stego.embed_text(A, "นัดบ่ายสาม ตึก 12", key="k1")
    assert r.n_failed == 0 and r.n_weak == 0
    assert stego.extract_text(attacks.apply("jpeg", r.image, 95), key="k1") == ("นัดบ่ายสาม ตึก 12", "ok")


def test_blocks_round_trip_and_raster_order():
    A = np.arange(8 * 12, dtype=float).reshape(8, 12)
    blocks = stego.to_blocks(A, 4)
    assert blocks.shape == (6, 4, 4)
    assert np.array_equal(blocks[1], A[0:4, 4:8])  # second block = top row, second column
    assert np.array_equal(stego.from_blocks(blocks, A.shape, 4), A)


def test_bytes_bits_round_trip():
    assert stego.bytes_to_bits(b"\x05").tolist() == [0, 0, 0, 0, 0, 1, 0, 1]
    assert stego.bits_to_bytes(stego.bytes_to_bits("ไทย".encode())) == "ไทย".encode()
