"""Logic behind the demo app.  Every operation calls the project's real code in src/svdmark.

Images travel between the browser and Python as base64 PNG data URLs.  All functions here are plain
functions (no web code), so tests/test_demo.py can check them directly.
"""

from __future__ import annotations

import base64
import csv
import io
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from svdmark import attacks, stego, watermark
from svdmark import ecc as ecc_mod
from svdmark.data import crop_to_multiple, to_gray
from svdmark.metrics import ncc, psnr

ROOT = Path(__file__).resolve().parents[1]

MAX_SIDE = 640  # larger photos are scaled down first (SVD of a 4000x3000 photo is slow)
LOG_FILE = Path(__file__).resolve().parent / "demo_log.csv"
CASES_FILE = Path(__file__).resolve().parent / "test_cases.json"

# The three modes offered to the user.  All use sigma_1 and delta = 4b (about 40.8 dB), as chosen in the pilot.
MODES = {
    "robust": {"b": 16, "delta": 64.0, "label": "ทนทาน (บล็อก 16×16)"},
    "balanced": {"b": 8, "delta": 32.0, "label": "สมดุล (บล็อก 8×8)"},
    "capacity": {"b": 4, "delta": 16.0, "label": "จุเยอะ (บล็อก 4×4)"},
}

# Sample photos from the BSDS500 evaluation set (shown only if data/images exists on this computer).
SAMPLES = [
    ("249061.jpg", "ภาพทั่วไป"),
    ("80099.jpg", "เรียบมาก (คอนทราสต์ต่ำ)"),
    ("189029.jpg", "ลายละเอียดเยอะ"),
    ("181021.jpg", "สว่างมาก"),
    ("42078.jpg", "มืดมาก"),
    ("196040.jpg", "มีส่วนขาวจัด (255)"),
]

STATUS_TEXT = {
    "ok": "พบข้อความ และตรวจ CRC ผ่าน: ข้อความถูกต้องครบทุกตัวอักษร",
    "no_message": "ไม่พบข้อความ: รูปนี้อาจไม่เคยซ่อนอะไร หรือรหัสลับ / โหมดไม่ตรงกับตอนซ่อน",
    "damaged": "พบหัวข้อความ แต่ CRC ไม่ผ่าน: ข้อความเสียหาย (รูปถูกบีบอัด ใส่สัญญาณรบกวน หรือดัดแปลง)",
}


# ---------------------------------------------------------------------------------------------- images
def decode_image(data_url: str) -> Image.Image:
    raw = base64.b64decode(data_url.split(",", 1)[-1])
    img = Image.open(io.BytesIO(raw))
    img.load()
    return img


def encode_png(a: np.ndarray) -> str:
    buf = io.BytesIO()
    Image.fromarray(np.clip(np.rint(a), 0, 255).astype(np.uint8), mode="L").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def gray_matrix(data_url: str, allow_resize: bool) -> tuple[np.ndarray, list[str]]:
    """Image -> grayscale float matrix whose sides are multiples of 16.  Returns (matrix, notes)."""
    img = decode_image(data_url)
    notes = []
    if allow_resize and max(img.size) > MAX_SIDE:
        s = MAX_SIDE / max(img.size)
        img = img.resize((max(16, round(img.width * s)), max(16, round(img.height * s))), Image.LANCZOS)
        notes.append(f"ย่อรูปให้ด้านยาวไม่เกิน {MAX_SIDE} พิกเซล เพื่อให้คำนวณเร็ว")
    if img.mode not in ("L",):
        notes.append("แปลงเป็นภาพขาวดำ (ระดับเทา) เพราะวิธีของเราทำกับภาพเทา")
    g = to_gray(img)
    h, w = g.shape
    g = crop_to_multiple(g, 16)
    if g.shape != (h, w):
        notes.append(f"ตัดขอบจาก {w}×{h} เป็น {g.shape[1]}×{g.shape[0]} ให้ด้านหาร 16 ลงตัว")
    return g, notes


def load_cover(data_url: str) -> dict:
    A, notes = gray_matrix(data_url, allow_resize=True)
    caps = {
        m: {
            "bits": stego.capacity(A.shape, p["b"]),
            "bytes": stego.text_capacity_bytes(A.shape, p["b"]),
            "bytes_ecc": stego.text_capacity_bytes(A.shape, p["b"], ecc=True),
        }
        for m, p in MODES.items()
    }
    return {"image": encode_png(A), "width": A.shape[1], "height": A.shape[0], "notes": notes, "capacity": caps}


def list_samples() -> list[dict]:
    out = []
    for name, label in SAMPLES:
        hits = list((ROOT / "data" / "images").glob(f"*/{name}"))
        if hits:
            buf = io.BytesIO(hits[0].read_bytes())
            out.append(
                {
                    "name": name,
                    "label": label,
                    "image": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
                }
            )
    return out


# ------------------------------------------------------------------------------------------ hide text
def _mode(mode: str) -> dict:
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    return MODES[mode]


def _key(key: str | None):
    return key if key else None


def stego_embed(cover: str, text: str, key: str, mode: str, ecc: bool = False) -> dict:
    A, _ = gray_matrix(cover, allow_resize=False)
    p = _mode(mode)
    if not text:
        return {"error": "ยังไม่ได้พิมพ์ข้อความ"}
    need, cap = stego.message_bits_needed(text, ecc), stego.capacity(A.shape, p["b"])
    if need > cap:
        return {
            "error": f"ข้อความยาว {len(text.encode('utf-8'))} ไบต์ (ต้องใช้ {need} บิต"
            f"{' รวมบิตแก้ผิด' if ecc else ''}) แต่รูปนี้ในโหมด{p['label']}"
            f"{' แบบแก้บิตผิด' if ecc else ''} จุได้ประมาณ {stego.text_capacity_bytes(A.shape, p['b'], ecc)} ไบต์ "
            f"ลองย่อข้อความ{' ปิดการแก้บิตผิด' if ecc else ''} หรือเปลี่ยนเป็นโหมดที่จุมากกว่า"
        }
    r = stego.embed_text(A, text, p["delta"], p["b"], key=_key(key), ecc=ecc)
    diff = np.abs(r.image - A)
    return {
        "image": encode_png(r.image),
        "diff": encode_png(np.clip(diff * 20, 0, 255)),
        "psnr": round(psnr(A, r.image), 2),
        "bits_used": need,
        "capacity": cap,
        "max_change": int(diff.max()),
        "changed_pct": round(100 * float((diff > 0).mean()), 1),
        "failed": r.n_failed,
        "weak": r.n_weak,
    }


def stego_extract(image: str, key: str, mode: str, ecc: bool = False) -> dict:
    B, notes = gray_matrix(image, allow_resize=False)
    p = _mode(mode)
    text, status, fixed = stego.extract_text(B, p["delta"], p["b"], key=_key(key), ecc=ecc, details=True)
    return {"status": status, "text": text, "explain": STATUS_TEXT[status], "notes": notes, "corrected": fixed}


ATTACK_LABEL = {
    "none": "ไม่โจมตี",
    "jpeg": "บันทึกเป็น JPEG คุณภาพ {}",
    "noise": "สัญญาณรบกวน σ = {}",
    "crop": "เจาะกลางภาพ {:.0%}",
    "resize": "ย่อเหลือ {:.0%} แล้วขยายกลับ",
    "blur": "เบลอ (รัศมี {} พิกเซล)",
    "median": "median filter {0}×{0}",
    "rotate": "หมุน {}°",
}


def attack_image(image: str, kind: str, level) -> tuple[np.ndarray, float | None, str]:
    A, _ = gray_matrix(image, allow_resize=False)
    if kind not in ATTACK_LABEL:
        raise ValueError(f"unknown attack {kind!r}")
    lv = None if kind == "none" else (int(level) if kind in ("jpeg", "noise", "median") else float(level))
    B = attacks.apply(kind, A, lv, seed=1)
    p = psnr(A, B)
    return B, (None if np.isinf(p) else round(p, 2)), ATTACK_LABEL[kind].format(lv)


def stego_attack_test(stego_image: str, text: str, key: str, mode: str, kind: str, level, ecc: bool = False) -> dict:
    """Attack the stego image, then read it back.  Also counts how many of the hidden bits flipped."""
    B, p_att, label = attack_image(stego_image, kind, level)
    p = _mode(mode)
    frame = stego.text_to_bits(text)
    sent = ecc_mod.encode(frame) if ecc else frame
    got = stego.extract_bits(B, len(sent), p["delta"], p["b"], key=_key(key))
    wrong = int((got != sent).sum())
    t, status, fixed = stego.extract_text(B, p["delta"], p["b"], key=_key(key), ecc=ecc, details=True)
    return {
        "image": encode_png(B),
        "attack": label,
        "psnr_attack": p_att,
        "bits": len(sent),
        "wrong_bits": wrong,
        "ber": round(100 * wrong / len(sent), 3),
        "status": status,
        "text": t,
        "explain": STATUS_TEXT[status],
        "corrected": fixed,
        "ecc": ecc,
    }


# ------------------------------------------------------------------------------------------ watermark
_WM_KEYS: dict[str, tuple[watermark.WatermarkKey, np.ndarray]] = {}


def logo_matrix(text: str, k: int) -> np.ndarray:
    """Render up to 8 Latin letters / digits as a k x k black-and-white logo (1 = white ink, 0 = background)."""
    text = re.sub(r"[^A-Za-z0-9 ]", "", text).strip().upper()[:8] or "SVD"
    img = Image.new("L", (k, k), 0)
    d = ImageDraw.Draw(img)
    lines = [text] if len(text) <= 4 else [text[: (len(text) + 1) // 2], text[(len(text) + 1) // 2 :]]
    size = k
    while size > 8:
        try:
            font = ImageFont.load_default(size=size)
        except TypeError:  # Pillow < 10.1: small bitmap font, scaled below
            font = ImageFont.load_default()
        boxes = [d.textbbox((0, 0), ln, font=font) for ln in lines]
        tw = max(b[2] - b[0] for b in boxes)
        th = sum(b[3] - b[1] for b in boxes) * 1.25
        if tw <= 0.86 * k and th <= 0.86 * k:
            break
        size = int(size * 0.9)
    y = (k - th) / 2
    for ln, bb in zip(lines, boxes, strict=True):
        w_, h_ = bb[2] - bb[0], bb[3] - bb[1]
        d.text(((k - w_) / 2 - bb[0], y - bb[1]), ln, fill=255, font=font)
        y += h_ * 1.25
    d.rectangle([3, 3, k - 4, k - 4], outline=255, width=max(2, k // 80))  # frame, so the logo area is obvious
    return (np.asarray(img) > 127).astype(float)


def logo_from_upload(data_url: str, k: int) -> np.ndarray:
    img = decode_image(data_url).convert("L").resize((k, k), Image.LANCZOS)
    a = np.asarray(img, dtype=float)
    return (a > a.mean()).astype(float)


def wm_embed(cover: str, alpha: float, logo_text: str = "", logo_image: str | None = None) -> dict:
    A, _ = gray_matrix(cover, allow_resize=False)
    k = min(A.shape)
    W = logo_from_upload(logo_image, k) if logo_image else logo_matrix(logo_text, k)
    Aw, key = watermark.embed(A, W, float(alpha))
    Au = np.clip(np.rint(Aw), 0, 255)
    kid = uuid.uuid4().hex[:12]
    _WM_KEYS[kid] = (key, W)
    p = psnr(A, Au)
    return {
        "image": encode_png(Au),
        "logo": encode_png(W * 255),
        "psnr": None if np.isinf(p) else round(p, 2),
        "diff": encode_png(np.clip(np.abs(Au - A) * 20, 0, 255)),
        "key_id": kid,
        "k": k,
    }


def wm_extract(image: str, key_id: str) -> dict:
    if key_id not in _WM_KEYS:
        return {"error": "ไม่พบ key ของลายน้ำ (เปิดแอปใหม่แล้วหรือยัง?) กรุณาฝังลายน้ำใหม่อีกครั้ง"}
    key, W = _WM_KEYS[key_id]
    B, _ = gray_matrix(image, allow_resize=False)
    if B.shape != (key.U.shape[0], key.Vt.shape[1]):
        return {"error": f"ขนาดรูป {B.shape[1]}×{B.shape[0]} ไม่ตรงกับรูปตอนฝังลายน้ำ"}
    s = watermark.singular_values(B)
    Ws = watermark.extract_from_sigma(s, key)
    shift = watermark.shift_from_sigma(s, key)
    nc = ncc(W, Ws)
    if shift >= 0.8:
        verdict = "shift score สูง: ค่า σ ของรูปนี้ขยับไปทางเดียวกับตอนฝังลายน้ำ → มีหลักฐานว่าฝังลายน้ำจริง"
    elif shift <= 0.3:
        verdict = "shift score ต่ำ: ค่า σ ไม่ได้ขยับไปทางที่การฝังทำ → ไม่มีหลักฐานว่ารูปนี้ถูกฝังลายน้ำ (แม้โลโก้จะดูเหมือนออกมาก็ตาม)"
    else:
        verdict = "shift score อยู่กลางๆ: รูปน่าจะถูกดัดแปลง (เช่น บีบอัดหรือมีสัญญาณรบกวน) ตัดสินแน่ชัดไม่ได้"
    return {
        "logo": encode_png(np.clip(Ws, 0, 1) * 255),
        "ncc": round(nc, 4),
        "shift": round(shift, 4),
        "verdict": verdict,
    }


def wm_attack(image: str, kind: str, level) -> dict:
    B, p_att, label = attack_image(image, kind, level)
    return {"image": encode_png(B), "attack": label, "psnr_attack": p_att}


# ------------------------------------------------------------------------------------------ test log
LOG_FIELDS = ["time", "tester", "case_id", "case", "expected", "observed", "matched", "note"]


def test_cases() -> list[dict]:
    return json.loads(CASES_FILE.read_text(encoding="utf-8"))


def log_result(tester: str, case_id: str, observed: str, matched: bool, note: str = "") -> dict:
    tester = tester.strip()
    if not tester:
        return {"error": "กรุณาใส่ชื่อผู้ทดสอบ"}
    case = next((c for c in test_cases() if c["id"] == case_id), None)
    if case is None:
        return {"error": f"ไม่รู้จักกรณีทดสอบ {case_id}"}
    new = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "tester": tester,
                "case_id": case_id,
                "case": case["title"],
                "expected": case["expected"],
                "observed": observed.strip(),
                "matched": "yes" if matched else "no",
                "note": note.strip(),
            }
        )
    return {"ok": True, "summary": log_summary()}


def log_summary() -> dict:
    if not LOG_FILE.exists():
        return {"rows": [], "testers": [], "cases_done": 0}
    with LOG_FILE.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return {
        "rows": rows[-30:],
        "testers": sorted({r["tester"] for r in rows}),
        "cases_done": len({r["case_id"] for r in rows}),
        "total": len(rows),
    }
