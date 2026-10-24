# ruff: noqa: E501  (long print lines: this script is for the screen recording, not for the report listing)
"""Many sample cases in one run -- for the recording and for checking the numbers quoted in the report.

Run from the repository root:   python examples/ex7_many_cases.py
Options:                        --quick   (skip part C)

Part A  steganography   hide a Thai message, damage the picture, read it back      (stego.py, ecc.py)
Part B  watermark       mark a picture with a logo, damage it, measure the mark    (watermark.py)
Part C  same message on 6 different photos                                         (capacity, PSNR)

Every number comes from the project code in src/svdmark; nothing is typed in by hand.
Attacks use seed 1, so the output is the same on every run.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from svdmark import attacks
from svdmark import ecc as ecc_mod
from svdmark.data import load_gray
from svdmark.metrics import ber, ncc, psnr
from svdmark.stego import (
    embed_text,
    extract_bits,
    extract_text,
    text_capacity_bytes,
    text_to_bits,
)
from svdmark.watermark import embed, extract, shift_score

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "data" / "images"
MSG = "นัดบ่ายสามที่ตึก 12"
KEY = "kmitl"
MODES = {  # same three modes as the demo: (block size b, step delta = 4b)
    "robust": (16, 64.0),
    "balanced": (8, 32.0),
    "capacity": (4, 16.0),
}
PHOTOS = [
    "249061.jpg",
    "80099.jpg",
    "189029.jpg",
    "181021.jpg",
    "42078.jpg",
    "196040.jpg",
]


def find(name: str) -> np.ndarray:
    hits = list(IMG.glob(f"*/{name}"))
    if not hits:
        sys.exit(
            f"photo {name} not found under {IMG} (put the BSDS500 images in data/images/)"
        )
    return load_gray(hits[0]).astype(float)


def table(title: str, header: list[str], rows: list[list[str]]) -> None:
    widths = [
        max(len(str(r[i])) for r in [header, *rows])
        for i in range(len(header))
    ]
    print(f"\n{title}")
    line = "  ".join(
        h.ljust(w) for h, w in zip(header, widths, strict=True)
    )
    print(line)
    print("-" * len(line))
    for r in rows:
        print(
            "  ".join(
                str(c).ljust(w) for c, w in zip(r, widths, strict=True)
            )
        )


def fmt_psnr(p: float) -> str:
    return "inf" if np.isinf(p) else f"{p:.2f}"


# ----------------------------------------------------------------------------- part A
def stego_case(
    name,
    A,
    mode="balanced",
    key=KEY,
    read_key=KEY,
    attack=("none", None),
    ecc=False,
    read_original=False,
):
    b, delta = MODES[mode]
    if read_original:
        S, p, sent = A, float("inf"), None
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = embed_text(A, MSG, delta, b, key=key, ecc=ecc)
        S, p = res.image, psnr(A, res.image)
        frame = text_to_bits(MSG)
        sent = ecc_mod.encode(frame) if ecc else frame
    B = attacks.apply(attack[0], S, attack[1], seed=1)
    text, status, fixed = extract_text(
        B, delta, b, key=read_key, ecc=ecc, details=True
    )
    wrong = "-"
    if sent is not None:
        got = extract_bits(B, len(sent), delta, b, key=read_key)
        wrong = f"{int((got != sent).sum())}/{len(sent)}"
    same = "yes" if text == MSG else "no"
    return [
        name,
        fmt_psnr(p),
        attacks.label(*attack),
        wrong,
        fixed,
        status,
        same,
    ]


def part_a(A: np.ndarray) -> None:
    rows = [
        stego_case("A1 balanced, no attack", A),
        stego_case("A2 right key", A, attack=("none", None)),
        stego_case("A3 wrong key (kmit1)", A, read_key="kmit1"),
        stego_case("A4 no key given", A, read_key=None),
        stego_case("A5 never-hidden photo", A, read_original=True),
        stego_case("A6 JPEG 90", A, attack=("jpeg", 90)),
        stego_case("A7 JPEG 50", A, attack=("jpeg", 50)),
        stego_case("A8 noise std 4", A, attack=("noise", 4)),
        stego_case(
            "A9 robust + noise std 8", A, mode="robust", attack=("noise", 8)
        ),
        stego_case("A10 balanced + crop 10%", A, attack=("crop", 0.10)),
        stego_case(
            "A11 capacity, JPEG 60, no ECC",
            A,
            mode="capacity",
            attack=("jpeg", 60),
        ),
        stego_case(
            "A12 capacity, JPEG 60, ECC",
            A,
            mode="capacity",
            attack=("jpeg", 60),
            ecc=True,
        ),
        stego_case("A13 rotate 0.5 deg", A, attack=("rotate", 0.5)),
    ]
    table(
        f'PART A  steganography, photo 249061.jpg {A.shape[1]}x{A.shape[0]}, message "{MSG}" '
        f"({len(MSG.encode())} bytes)",
        [
            "case",
            "PSNR dB",
            "attack",
            "wrong bits",
            "fixed",
            "status",
            "text same",
        ],
        rows,
    )
    print(
        "\nstatus: ok = CRC passed | damaged = header fits but CRC failed | no_message = header makes no sense"
    )
    print(
        "wrong bits = bits read back differently from the bits hidden (BER = wrong / total); fixed = bits Hamming corrected"
    )
    print(
        "PSNR is high here because a short message changes only a few blocks; a message that fills the photo gives about 41 dB"
    )
    print(
        "(report: 40.7 dB average over 400 photos).  With ECC the same text needs 7/4 as many blocks (770 bits instead of 440)."
    )
    b, delta = MODES["balanced"]
    long_msg = "ก" * 120  # 360 bytes > 296 bytes
    try:
        embed_text(A, long_msg, delta, b)
    except ValueError as e:
        print(
            f"A14 message of {len(long_msg.encode())} bytes -> refused: {e}"
        )


# ----------------------------------------------------------------------------- part B
def make_logo(k: int) -> np.ndarray:
    """A k x k black-and-white test logo: frame, two diagonals and a filled square (1 = ink)."""
    img = Image.new("L", (k, k), 0)
    d = ImageDraw.Draw(img)
    d.rectangle([4, 4, k - 5, k - 5], outline=255, width=max(2, k // 80))
    d.line(
        [(k // 8, k // 8), (7 * k // 8, 7 * k // 8)],
        fill=255,
        width=max(2, k // 40),
    )
    d.line(
        [(7 * k // 8, k // 8), (k // 8, 7 * k // 8)],
        fill=255,
        width=max(2, k // 40),
    )
    d.rectangle([3 * k // 8, 3 * k // 8, 5 * k // 8, 5 * k // 8], fill=255)
    return (np.asarray(img) > 127).astype(float)


def wm_case(name, A, alpha=16.0, attack=("none", None), target="marked"):
    W = make_logo(min(A.shape))
    Aw, key = embed(A, W, alpha)
    Au = np.clip(np.rint(Aw), 0, 255)
    T = Au if target == "marked" else A
    B = attacks.apply(attack[0], T, attack[1], seed=1)
    shift = shift_score(B, key)
    verdict = (
        "mark found"
        if shift >= 0.8
        else ("no mark" if shift <= 0.3 else "unsure")
    )
    return [
        name,
        f"{alpha:g}",
        fmt_psnr(psnr(A, Au)),
        attacks.label(*attack),
        f"{ncc(W, extract(B, key)):.3f}",
        f"{shift:.3f}",
        verdict,
    ]


def part_b(A: np.ndarray) -> None:
    rows = [
        wm_case("B1 embed, no attack", A),
        wm_case("B2 never-marked photo", A, target="original"),
        wm_case("B3 JPEG 75", A, attack=("jpeg", 75)),
        wm_case(
            "B4 alpha too weak (2) + JPEG 75",
            A,
            alpha=2.0,
            attack=("jpeg", 75),
        ),
        wm_case("B5 rotate 1 deg", A, attack=("rotate", 1.0)),
        wm_case("B6 blur radius 1", A, attack=("blur", 1.0)),
        wm_case("B7 noise std 4", A, attack=("noise", 4)),
    ]
    table(
        "PART B  watermark D = S + alpha*W (Liu-Tan), same photo",
        ["case", "alpha", "PSNR dB", "attack", "NCC", "shift", "verdict"],
        rows,
    )
    print(
        "\nNCC = how much the extracted logo looks like the real one (it is high even for B2: the key itself holds the logo)."
    )
    print(
        "shift = cos(sigma(received) - S, Sw - S): near 1 if the singular values moved the way embedding moves them."
    )
    print(
        "verdict thresholds 0.8 / 0.3 are the rough demo values (see results/findings.md for their limits)."
    )


# ----------------------------------------------------------------------------- part C
def part_c() -> None:
    rows = []
    for n in PHOTOS:
        A = find(n)
        b, delta = MODES["balanced"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = embed_text(A, MSG, delta, b, key=KEY)
        B = attacks.apply("jpeg", res.image, 90, seed=1)
        text, status = extract_text(B, delta, b, key=KEY)
        sent = text_to_bits(MSG)
        got = extract_bits(B, len(sent), delta, b, key=KEY)
        rows.append(
            [
                n,
                f"{A.shape[1]}x{A.shape[0]}",
                text_capacity_bytes(A.shape, b),
                fmt_psnr(psnr(A, res.image)),
                f"{ber(sent, got):.3f}",
                status,
                "yes" if text == MSG else "no",
            ]
        )
    table(
        "PART C  same message, balanced mode, JPEG 90, six different photos",
        [
            "photo",
            "size",
            "capacity B",
            "PSNR dB",
            "BER",
            "status",
            "text same",
        ],
        rows,
    )
    print(
        "\nThe same short message gives about the same PSNR on every photo.  The report's 40.7 dB is the average over 400 photos"
    )
    print(
        "with a message that fills the photo; PSNR falls as more blocks are used."
    )


def main() -> None:
    A = find("249061.jpg")
    part_a(A)
    part_b(A)
    if "--quick" not in sys.argv:
        part_c()


if __name__ == "__main__":
    main()
