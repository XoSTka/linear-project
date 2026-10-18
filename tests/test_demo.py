"""The demo app's logic (demo/core.py) uses the real code; check its main paths without a browser."""

import numpy as np
import pytest

import core  # demo/core.py; pyproject.toml puts demo/ on the test import path


@pytest.fixture
def cover():
    rng = np.random.default_rng(0)
    y, x = np.mgrid[0:321, 0:481]
    img = 110 + 50 * np.sin(x / 13) + 35 * np.cos(y / 9) + rng.normal(0, 5, (321, 481))
    return core.load_cover(core.encode_png(img))


def test_load_crops_to_16(cover):
    assert (cover["width"], cover["height"]) == (480, 320)
    assert cover["capacity"]["balanced"] == {"bits": 2400, "bytes": 296, "bytes_ecc": 167}


def test_stego_round_trip_and_wrong_key(cover):
    e = core.stego_embed(cover["image"], "นัดบ่ายสาม ตึก 12", "kmitl", "balanced")
    assert e["failed"] == 0 and e["psnr"] > 40
    assert core.stego_extract(e["image"], "kmitl", "balanced")["text"] == "นัดบ่ายสาม ตึก 12"
    assert core.stego_extract(e["image"], "kmit1", "balanced")["status"] != "ok"
    assert core.stego_extract(cover["image"], "", "balanced")["status"] != "ok"


def test_too_long_message_gives_readable_error(cover):
    r = core.stego_embed(cover["image"], "ก" * 30, "", "robust")
    assert "error" in r and "71" in r["error"]


def test_attack_counts_wrong_bits(cover):
    e = core.stego_embed(cover["image"], "hello", "", "balanced")
    r = core.stego_attack_test(e["image"], "hello", "", "balanced", "crop", 0.25)
    assert r["bits"] == 72 and 0 <= r["wrong_bits"] <= 72


def test_logo_is_binary_and_framed():
    W = core.logo_matrix("LA2026", 320)
    assert W.shape == (320, 320) and set(np.unique(W)) <= {0.0, 1.0}
    assert 0.05 < W.mean() < 0.6


def test_watermark_false_positive_is_flagged(cover):
    w = core.wm_embed(cover["image"], 16, "LA2026")
    marked = core.wm_extract(w["image"], w["key_id"])
    never = core.wm_extract(cover["image"], w["key_id"])
    assert marked["shift"] > 0.8 and marked["ncc"] > 0.99
    # NCC is still clearly positive (about 0.98 on real photos, lower on this synthetic image); the shift score is 0
    assert never["shift"] == 0.0 and never["ncc"] > 0.5


def test_ecc_mode_round_trip_and_extra_attack(cover):
    e = core.stego_embed(cover["image"], "นัดบ่ายสาม", "k", "balanced", ecc=True)
    assert core.stego_extract(e["image"], "k", "balanced", ecc=True)["text"] == "นัดบ่ายสาม"
    r = core.stego_attack_test(e["image"], "นัดบ่ายสาม", "k", "balanced", "rotate", 1.0, ecc=True)
    assert r["status"] != "ok"  # rotation breaks the block grid: an honest failure
    assert core.attack_image(cover["image"], "resize", 0.5)[2].startswith("Resize")


HAVE_SAMPLES = all(list((core.ROOT / "data" / "images").glob(f"*/{n}")) for n, _ in core.SAMPLES)


@pytest.mark.skipif(not HAVE_SAMPLES, reason="BSDS500 sample photos not in data/images")
def test_every_prepared_case_gives_the_expected_result():
    for case in core.test_cases():
        r = core.run_case(case["id"])
        got = [(x["label"], x.get("status") or x.get("shift"), x["auto"]) for x in r["runs"]]
        assert r["auto"] is True, (case["id"], got)


def test_prepared_cases_are_well_formed():
    cases = core.test_cases()
    assert len(cases) >= 10 and len({c["id"] for c in cases}) == len(cases)
    for c in cases:
        assert c["kind"] in ("stego", "wm") and c["runs"] and c["title"] and c["expected"] and c["settings"]
        for r in c["runs"]:
            assert r["image"] in dict(core.SAMPLES)
            assert r["attack"][0] in core.ATTACK_LABEL
            if c["kind"] == "stego":
                assert r["mode"] in core.MODES


@pytest.mark.skipif(not HAVE_SAMPLES, reason="BSDS500 sample photos not in data/images")
def test_case_can_run_on_another_photo(cover):
    r = core.run_case("S2", "189029.jpg")
    assert r["custom_image"] and r["runs"][0]["status"] == "ok"
    r = core.run_case("S3", cover["image"])  # an uploaded photo (data URL)
    assert r["runs"][0]["status"] != "ok"
