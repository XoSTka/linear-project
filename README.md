# SVD-based Digital Watermarking & Steganography

โครงงานวิชาเวกเตอร์และเมทริกซ์ (พีชคณิตเชิงเส้น) — ฝังลายน้ำ (watermarking แบบ Liu–Tan) และซ่อนข้อความลับ (steganography แบบ QIM บนค่า σ ของบล็อก) ในภาพระดับเทาด้วย Singular Value Decomposition (SVD)

สถานะ: อยู่ระหว่างพัฒนา (work in progress)

## โครงสร้าง repo

```
src/svdmark/   โค้ดหลัก (svd_utils, watermark, stego, attacks, metrics, data)
tests/         unit test ยืนยันตัวอย่างคำนวณมือ + round-trip
experiments/   สคริปต์รันการทดลอง (pilot และเต็มรูปแบบ)
results/       ผลลัพธ์: CSV, กราฟ, ตาราง .tex
notebooks/     demo แสดงภาพก่อน/หลังฝัง
```

## การติดตั้ง

```bash
pip install -r requirements.txt
```

## การรัน (จะเพิ่มรายละเอียดเมื่อมีโค้ด)

```bash
pytest tests/
```
