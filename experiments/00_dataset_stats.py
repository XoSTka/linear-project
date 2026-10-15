"""
Step 1 (data prep): สำรวจสถิติเบื้องต้นของ dataset BSDS500 ที่ดาวน์โหลดมา
รัน: python experiments/00_dataset_stats.py
ผลลัพธ์: results/dataset_stats.csv + สรุปสถิติพิมพ์ออกหน้าจอ (ใช้ในรายงานหัวข้อ "การเตรียมข้อมูล")
"""
import os
import csv
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "images"
OUT_CSV = ROOT / "results" / "dataset_stats.csv"

SPLITS = ["train", "val", "test"]


def collect_rows():
    rows = []
    for split in SPLITS:
        split_dir = DATA_DIR / split
        for fp in sorted(split_dir.glob("*.jpg")):
            with Image.open(fp) as im:
                w, h = im.size
                mode = im.mode
            size_kb = fp.stat().st_size / 1024
            rows.append({
                "split": split,
                "filename": fp.name,
                "width": w,
                "height": h,
                "mode": mode,
                "size_kb": round(size_kb, 1),
            })
    return rows


def summarize(rows):
    n = len(rows)
    widths = [r["width"] for r in rows]
    heights = [r["height"] for r in rows]
    sizes = [r["size_kb"] for r in rows]
    modes = {}
    for r in rows:
        modes[r["mode"]] = modes.get(r["mode"], 0) + 1
    split_counts = {}
    for r in rows:
        split_counts[r["split"]] = split_counts.get(r["split"], 0) + 1

    split_pct = {k: round(v / n * 100, 1) for k, v in split_counts.items()}
    mode_pct = {k: round(v / n * 100, 1) for k, v in modes.items()}

    print(f"จำนวนภาพทั้งหมด: {n}")
    print(f"แบ่งตามชุด: {split_counts}  (สัดส่วน % = {split_pct})")
    print(f"โหมดสี: {modes}  (สัดส่วน % = {mode_pct})")
    print(f"ความกว้าง (px): เฉลี่ย={sum(widths)/n:.1f} สูงสุด={max(widths)} ต่ำสุด={min(widths)}")
    print(f"ความสูง (px): เฉลี่ย={sum(heights)/n:.1f} สูงสุด={max(heights)} ต่ำสุด={min(heights)}")
    print(f"ขนาดไฟล์ (KB): เฉลี่ย={sum(sizes)/n:.1f} สูงสุด={max(sizes)} ต่ำสุด={min(sizes)}")


def main():
    rows = collect_rows()
    OUT_CSV.parent.mkdir(exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["split", "filename", "width", "height", "mode", "size_kb"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"บันทึก: {OUT_CSV}\n")
    summarize(rows)


if __name__ == "__main__":
    main()
