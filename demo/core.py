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
    "robust": {"b": 16, "delta": 64.0, "label": "Robust"},
    "balanced": {"b": 8, "delta": 32.0, "label": "Balanced"},
    "capacity": {"b": 4, "delta": 16.0, "label": "Capacity"},
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
    "ok": "อ่านได้ครบ: CRC ผ่าน ได้ข้อความเดิมทุกตัวอักษร",
    "no_message": "ไม่พบข้อความ: รูปนี้ไม่เคยซ่อนอะไร หรือ key / mode ไม่ตรงกับตอนซ่อน",
    "damaged": "ข้อความเสียหาย: เจอข้อความ แต่ CRC ไม่ผ่าน (รูปถูกบีบอัด มี noise หรือถูกแก้)",
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
        notes.append(f"ย่อให้ด้านยาวไม่เกิน {MAX_SIDE} px")
    if img.mode not in ("L",):
        notes.append("แปลงเป็นภาพเทา")
    g = to_gray(img)
    h, w = g.shape
    g = crop_to_multiple(g, 16)
    if g.shape != (h, w):
        notes.append(f"ตัดขอบจาก {w}×{h} (ด้านต้องหาร 16 ลงตัว)")
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
            "error": f"ข้อความยาว {len(text.encode('utf-8'))} bytes แต่รูปนี้ใน mode {p['label']}"
            f"{' + ECC' if ecc else ''} จุได้ {stego.text_capacity_bytes(A.shape, p['b'], ecc)} bytes "
            f"ลองย่อข้อความ{' ปิด ECC' if ecc else ''} หรือเปลี่ยนเป็น mode ที่จุมากกว่า"
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
    "none": "none",
    "jpeg": "JPEG Q{}",
    "noise": "Gaussian noise σ={}",
    "crop": "Crop center {:.0%}",
    "resize": "Resize {:.0%} → 100%",
    "blur": "Blur r={:g}",
    "median": "Median {0}×{0}",
    "rotate": "Rotate {:g}°",
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
    evidence, verdict = _wm_verdict(shift)
    return {
        "logo": encode_png(np.clip(Ws, 0, 1) * 255),
        "ncc": round(nc, 4),
        "shift": round(shift, 4),
        "evidence": evidence,
        "verdict": verdict,
    }


def _wm_verdict(shift: float) -> tuple[str, str]:
    """Thresholds 0.8 / 0.3 are rough demo values (results/findings.md: they do not hold after blurring)."""
    if shift >= 0.8:
        return "yes", "มีลายน้ำของเรา: σ ของรูปขยับไปทางเดียวกับตอนฝัง"
    if shift <= 0.3:
        return "no", "ไม่มีลายน้ำของเรา: σ ไม่ได้ขยับแบบตอนฝัง (แม้โลโก้จะขึ้นมาก็ตาม)"
    return "unsure", "ไม่แน่ใจ: รูปน่าจะถูกแก้ไข (เช่น บีบอัด หรือมี noise) ตัดสินแน่ชัดไม่ได้"


def wm_attack(image: str, kind: str, level) -> dict:
    B, p_att, label = attack_image(image, kind, level)
    return {"image": encode_png(B), "attack": label, "psnr_attack": p_att}


# ------------------------------------------------------------------------------------------ test log
LOG_FIELDS = ["time", "tester", "case_id", "case", "expected", "observed", "matched", "note"]


def test_cases() -> list[dict]:
    return json.loads(CASES_FILE.read_text(encoding="utf-8"))


def log_result(tester: str, case_id: str, observed: str, matched: bool, note: str = "") -> dict:
    tester = tester.strip() or "ไม่ระบุชื่อ"
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


def log_csv() -> bytes:
    """The whole log file (UTF-8 with BOM so Excel shows Thai correctly); header only if nothing was logged yet."""
    if LOG_FILE.exists():
        return LOG_FILE.read_bytes()
    return ("\ufeff" + ",".join(LOG_FIELDS) + "\r\n").encode("utf-8")


# ----------------------------------------------------------------------------------- prepared cases
def sample_matrix(name: str) -> np.ndarray:
    """A sample photo from data/images as the grayscale matrix the demo uses (sides cut to multiples of 16)."""
    if name not in dict(SAMPLES):
        raise ValueError(f"unknown sample {name!r}")
    hits = list((ROOT / "data" / "images").glob(f"*/{name}"))
    if not hits:
        raise FileNotFoundError(f"ไม่พบรูปตัวอย่าง {name} (ยังไม่ได้วางชุด BSDS500 ไว้ใน data/images)")
    return crop_to_multiple(to_gray(Image.open(hits[0])), 16)


def _check(expect: dict | None, r: dict) -> bool | None:
    """Did one run give the expected result?  None = this run has no automatic check (shown for comparison)."""
    if not expect:
        return None
    if "refused" in expect:
        return "error" in r
    if "status" in expect:
        return r.get("status") == expect["status"] and r.get("text") == r.get("sent_text")
    if "not_ok" in expect:
        return r.get("status") in ("no_message", "damaged")
    ok = True
    if "shift_min" in expect:
        ok &= r["shift"] >= expect["shift_min"]
    if "shift_max" in expect:
        ok &= r["shift"] <= expect["shift_max"]
    if "shift_below" in expect:
        ok &= r["shift"] < expect["shift_below"]
    if "psnr_min" in expect:
        ok &= r["psnr"] is None or r["psnr"] >= expect["psnr_min"]
    return bool(ok)


def _case_matrix(run: dict, image: str | None) -> np.ndarray:
    """The run's own sample photo, or the photo the user picked instead (a sample name or an uploaded data URL)."""
    if not image:
        return sample_matrix(run["image"])
    if image.startswith("data:"):
        return gray_matrix(image, allow_resize=True)[0]
    return sample_matrix(image)


def _run_stego(run: dict, image: str | None = None) -> dict:
    A = _case_matrix(run, image)
    p = _mode(run["mode"])
    out = {"label": run["label"], "cover": encode_png(A), "sent_text": run["text"]}
    if run["read_original"]:
        S = A
    else:
        need, cap = stego.message_bits_needed(run["text"], run["ecc"]), stego.capacity(A.shape, p["b"])
        if need > cap:
            byts = stego.text_capacity_bytes(A.shape, p["b"], run["ecc"])
            n = len(run["text"].encode("utf-8"))
            out["error"] = f"ไม่ซ่อน: ข้อความยาว {n} bytes แต่ mode {p['label']} จุได้ {byts} bytes"
            return out
        r = stego.embed_text(A, run["text"], p["delta"], p["b"], key=_key(run["key"]), ecc=run["ecc"])
        S = r.image
        out["stego"] = encode_png(S)
        out["psnr"] = round(psnr(A, S), 2)
    kind, level = run["attack"]
    B = attacks.apply(kind, S, level, seed=1) if kind != "none" else S
    out["attack"] = ATTACK_LABEL[kind].format(level)
    if kind != "none":
        out["attacked"] = encode_png(B)
    read_key = _key(run["read_key"])
    text, status, fixed = stego.extract_text(B, p["delta"], p["b"], key=read_key, ecc=run["ecc"], details=True)
    out.update(status=status, text=text, explain=STATUS_TEXT[status], corrected=fixed)
    if not run["read_original"]:
        frame = stego.text_to_bits(run["text"])
        sent = ecc_mod.encode(frame) if run["ecc"] else frame
        got = stego.extract_bits(B, len(sent), p["delta"], p["b"], key=_key(run["read_key"]))
        out["bits"], out["wrong_bits"] = len(sent), int((got != sent).sum())
    return out


def _run_wm(run: dict, image: str | None = None) -> dict:
    A = _case_matrix(run, image)
    W = logo_matrix(run["logo"], min(A.shape))
    Aw, key = watermark.embed(A, W, float(run["alpha"]))
    Au = np.clip(np.rint(Aw), 0, 255)
    T = Au if run["target"] == "marked" else A
    kind, level = run["attack"]
    B = attacks.apply(kind, T, level, seed=1) if kind != "none" else T
    s = watermark.singular_values(B)
    shift = watermark.shift_from_sigma(s, key)
    evidence, verdict = _wm_verdict(shift)
    p = psnr(A, Au)
    return {
        "label": run["label"],
        "target": run["target"],
        "cover": encode_png(A),
        "stego": encode_png(Au),
        "attacked": encode_png(B) if kind != "none" else None,
        "attack": ATTACK_LABEL[kind].format(level),
        "psnr": None if np.isinf(p) else round(p, 2),
        "logo": encode_png(np.clip(watermark.extract_from_sigma(s, key), 0, 1) * 255),
        "ncc": round(ncc(W, watermark.extract_from_sigma(s, key)), 4),
        "shift": round(shift, 4),
        "evidence": evidence,
        "verdict": verdict,
    }


def run_case(case_id: str, image: str | None = None) -> dict:
    """Run one prepared case end to end (hide or watermark -> attack -> read back) and check it automatically.

    `image` (optional) replaces the case's own photo(s): a sample name from SAMPLES or an uploaded data URL.
    The expected results were written for the case's own photos, so another photo can change the outcome.
    """
    case = next((c for c in test_cases() if c["id"] == case_id), None)
    if case is None:
        return {"error": f"ไม่รู้จักกรณีทดสอบ {case_id}"}
    runner = _run_stego if case["kind"] == "stego" else _run_wm
    runs = [runner(r, image) for r in case["runs"]]
    for spec, r in zip(case["runs"], runs, strict=True):
        r["auto"] = _check(spec.get("expect"), r)
        r.pop("sent_text", None)
    for i, spec in enumerate(case["runs"]):  # cross-run check: marked image must score higher than the next one
        if (spec.get("expect") or {}).get("higher_than_next"):
            runs[i]["auto"] = runs[i]["shift"] > runs[i + 1]["shift"]
    checks = [r["auto"] for r in runs if r["auto"] is not None]
    return {"id": case_id, "runs": runs, "auto": all(checks) if checks else None, "custom_image": bool(image)}
