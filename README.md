# SVD-based Digital Watermarking & Steganography

โครงงานวิชาพีชคณิตเชิงเส้น: ใช้ Singular Value Decomposition (SVD) ทำงาน 2 อย่างกับภาพระดับเทา

1. **ฝังลายน้ำ (watermarking)** ตามวิธีของ Liu & Tan (2002) คือบวกลายน้ำเข้าไปในค่า singular value ของทั้งภาพ
2. **ซ่อนข้อความลับ (steganography)** ด้วย QIM คือแบ่งภาพเป็นบล็อก b×b แล้วขยับ singular value ของแต่ละบล็อกให้ไปตกในช่วงที่แทนบิต 0 หรือ 1 (บล็อกละ 1 บิต) มีการตรวจซ้ำหลังปัดเศษพิกเซล (closed-loop พร้อมระยะเผื่อ Δ/4), รหัสลับ (สร้างตำแหน่งเส้นแบ่งด้วย PBKDF2) และเลือกเปิดการแก้บิตผิดด้วย Hamming(7,4) ได้

ผลทั้งหมดพร้อมตัวเลขอยู่ใน [`results/findings.md`](results/findings.md) ส่วนเหตุผลที่เลือกพารามิเตอร์อยู่ใน [`results/pilot_decisions.md`](results/pilot_decisions.md)

## ข้อมูล

ใช้ภาพ **BSDS500** (Berkeley Segmentation Dataset 500) ทั้ง 500 ภาพ ขนาด 481×321 หรือ 321×481 พิกเซล
ที่มา: Arbeláez, Maire, Fowlkes & Malik, "Contour Detection and Hierarchical Image Segmentation", IEEE TPAMI 33(5), 2011
ดาวน์โหลด: <https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/resources.html>

ภาพไม่ได้อยู่ใน repo (ไฟล์ใหญ่ และเป็นลิขสิทธิ์ของเจ้าของชุดข้อมูล) ให้ดาวน์โหลดแล้ววางตามนี้

```
data/images/train/*.jpg   (200 ภาพ)
data/images/val/*.jpg     (100 ภาพ)
data/images/test/*.jpg    (200 ภาพ)
```

**การแบ่งชุดภาพ** เราไม่ได้เทรนโมเดล จึงใช้ชื่อ split ของ BSDS500 เป็นแค่การแบ่งที่ตายตัว

| ชุด | ภาพ | ใช้ทำอะไร |
|---|---|---|
| pilot | `val` 100 ภาพ | เลือกพารามิเตอร์เท่านั้น (b, Δ, σ ตัวที่ใช้, α) |
| eval | `train` + `test` 400 ภาพ | ตัวเลขทุกตัวที่รายงาน ไม่เคยใช้จูนค่า |

**การเตรียมภาพ** (ไฟล์ `src/svdmark/data.py`) แปลงเป็นระดับเทาด้วยสูตร 0.299R + 0.587G + 0.114B แล้วตัดขอบตรงกลางให้ด้านทั้งสองหาร 16 ลงตัว ได้ 480×320 (หรือ 320×480) ไม่มีการย่อหรือขยายภาพ

## ติดตั้ง

ใช้ Python 3.10 ขึ้นไป รันคำสั่งนี้ในโฟลเดอร์โปรเจกต์

```bash
pip install -r requirements.txt
```

คำสั่งนี้ติดตั้งแพ็กเกจ `svdmark` ของเราเอง (โค้ดใน `src/svdmark` ตั้งค่าไว้ใน `pyproject.toml`) แบบ editable คือแก้โค้ดแล้วมีผลทันทีโดยไม่ต้องติดตั้งใหม่ พร้อมไลบรารีที่ต้องใช้ทั้งหมด สคริปต์การทดลองและเดโมจึง `import svdmark` ได้จากทุกที่

## รัน

```bash
pytest                              # เทสต์ทั้งหมด (เทสต์ที่ใช้ภาพจริงจะข้ามไปถ้ายังไม่มีภาพ)
ruff check . && ruff format --check .   # (ไม่บังคับ) ตรวจรูปแบบโค้ด ต้องติดตั้ง ruff ก่อน: pip install ruff
python experiments/run_all.py       # รันการทดลองทั้งหมดตามลำดับ (~1 ชั่วโมงบนเครื่อง 2 คอร์)
```

`run_all.py` เรียกสคริปต์ตามลำดับนี้ (เรียกทีละขั้นได้ เช่น `python experiments/run_all.py full_stego`) และเก็บ log ไว้ใน `logs/`

| ขั้น | สคริปต์ | ผลลัพธ์ |
|---|---|---|
| 1 | `prepare_data.py` | `results/image_sets.csv`, `results/sigma_eval.csv` |
| 2 | `pilot_stego.py`, `pilot_watermark.py` | `results/pilot_*.csv` (ชุด pilot) |
| 3 | `full_stego.py`, `full_watermark.py` | `results/stego_full.csv`, `results/watermark_full.csv` (ชุด eval) |
| 4 | `analyze_stego.py`, `analyze_watermark.py` | `results/*_summary.csv`, `results/watermark_detection.csv` |
| 5 | `steganalysis.py`, `ml_steganalysis.py` | `results/steganalysis*.csv`, `results/ml_*.csv` (ตัวสถิติ R และตัวตรวจแบบ machine learning) |
| 5b | `robustness_extra.py`, `key_strength.py` | ข้อความทั้งก้อนรอดไหม (เปิด/ปิด Hamming, การโจมตีเพิ่ม: ย่อขยาย เบลอ หมุน), ความแข็งแรงของรหัสลับ |
| 6 | `theory_checks.py` | `results/theory_checks.csv` |
| 7 | `make_report_assets.py` | `results/figures/*.png`, `results/tables/*.csv / *.tex` |

ทุกขั้นใช้ seed คงที่ รันซ้ำจะได้ตัวเลขเดิม

## เดโม (แอปในเบราว์เซอร์)

```bash
python demo/app.py          # เปิด http://127.0.0.1:8765 ให้อัตโนมัติ (กด Ctrl+C เพื่อปิด)
```

ใช้แค่แพ็กเกจใน requirements.txt (ตัวเว็บเซิร์ฟเวอร์คือ `http.server` ที่มากับ Python) ทุกปุ่มเรียกโค้ดจริงใน `src/svdmark` และทำงานบนเครื่องนี้ทั้งหมด

- **ซ่อนข้อความ** (หน้าแรก) จัดเป็น 3 ส่วน: ผู้ส่ง (รูป, ข้อความพร้อมแถบความจุ, key, mode Robust / Balanced / Capacity, Hamming ECC) → ระหว่างทาง (จำลอง attack เช่น JPEG, noise, crop, rotate) → ผู้รับ (Decode รูปที่เพิ่งซ่อน หรืออัปโหลดรูปที่ได้รับมา) · ตรงกลางเทียบ Original กับรูปที่ซ่อนแล้ว ได้ทั้งแบบลากเส้นแบ่งและแบบวางคู่กัน (หลัง Encode จะวางคู่กันให้อัตโนมัติ) / จุดที่ถูกแก้ ×20 / รูปหลัง attack · ดาวน์โหลด PNG ได้ · คลิกรูปหรือปุ่ม "ขยายดู" เพื่อซูมดูทีละพิกเซล (รูปในกลุ่มเดียวกันซูมพร้อมกัน)
- **Watermark** ฝังโลโก้ด้วย α ที่เลือก (พิมพ์ตัวอักษร หรืออัปโหลดรูปของตัวเอง ซึ่งจะถูกแปลงเป็นขาวดำขนาดเท่า Σ ของรูป) แล้วตรวจรูปที่ฝังเทียบกับรูปต้นฉบับที่ไม่เคยฝัง (เลือก attack ก่อนตรวจได้) เพื่อดูว่าทำไม NCC อย่างเดียวเชื่อไม่ได้ และ shift score แยกได้ · จอกลางดูรูปหลัง attack และเทียบโลโก้ที่ดึงออกมาขนาดใหญ่ได้
- **ชุดทดสอบ** 20 กรณีที่ตั้งค่าไว้แล้ว (`demo/test_cases.json`) เลือกรูปที่ใช้ทดสอบได้ (รูปตามที่ตั้งไว้ รูปตัวอย่างอื่น หรืออัปโหลด) กด Run (หรือ Run all) ระบบจะซ่อน → attack → อ่านกลับ และเช็คกับผลที่คาดให้อัตโนมัติ จากนั้นผู้ลองกดยืนยันผล ซึ่งบันทึกลง `demo/demo_log.csv` (ดาวน์โหลดได้จากปุ่ม Export CSV)

ฟอนต์ Sarabun และ IBM Plex Mono อยู่ใน `demo/static/fonts` (SIL Open Font License) แอปจึงใช้ได้แม้ไม่มีอินเทอร์เน็ต

รูปตัวอย่างในแอปมาจาก `data/images` (ถ้ายังไม่ได้วางชุด BSDS500 ก็อัปโหลดรูปเองได้)

## ใช้ซ่อนข้อความเอง

```python
from svdmark.data import load_gray
from svdmark import stego

A = load_gray("photo.jpg")                                   # ภาพเทา 0..255
r = stego.embed_text(A, "สวัสดี", key="รหัสลับ")              # ค่าตั้งต้น: σ₁, b = 8, Δ = 32
text, status = stego.extract_text(r.image, key="รหัสลับ")     # ("สวัสดี", "ok")

r = stego.embed_text(A, "สวัสดี", key="รหัสลับ", ecc=True)    # เปิดแก้บิตผิด Hamming(7,4): ทนกว่า แต่จุได้ 4/7
text, status = stego.extract_text(r.image, key="รหัสลับ", ecc=True)
```

สถานะที่ได้จาก `extract_text`
- `ok` ข้อความถูกต้องครบ (CRC ตรง)
- `no_message` ไม่พบข้อความ (ภาพที่ไม่เคยซ่อนอะไร หรือใช้รหัสผิด)
- `damaged` พบหัวข้อความแต่เนื้อหาเสีย (เช่น ภาพโดนบีบอัดหรือมีสัญญาณรบกวน)

ความจุ: b=8 ได้ 2,400 บิตต่อภาพ 480×320 หักหัวข้อความ 32 บิต เหลือประมาณ 296 ไบต์ (ภาษาไทยใช้ 3 ไบต์ต่อตัวอักษร จึงได้ประมาณ 98 ตัว) ถ้าเปิด Hamming เหลือ 167 ไบต์

## โครงสร้าง repo

```
src/svdmark/
  svd_utils.py   SVD, การสร้างเมทริกซ์กลับ, SVD 2×2 แบบคำนวณมือ
  stego.py       ซ่อนข้อความ: กฎ QIM, closed-loop, รหัสลับ (PBKDF2), การแปลงข้อความ <-> บิต
  ecc.py         รหัสแก้บิตผิด Hamming(7,4): เมทริกซ์ G, H และ syndrome
  watermark.py   ลายน้ำ Liu–Tan และ shift_score (ตัวตรวจที่เราเสนอเพิ่ม)
  attacks.py     การโจมตี: สัญญาณรบกวน Gaussian, JPEG, เจาะภาพ (crop)
  metrics.py     MSE, RMS, PSNR, NCC, BER, AUC (ใช้วัดว่าตัวตรวจแยกภาพได้ดีแค่ไหน)
  data.py        โหลดภาพ, แปลงเทา, ตัดขอบ, ชุด pilot / eval
tests/           เทสต์ (ตัวอย่างคำนวณมือ, ซ่อนแล้วอ่านกลับ, ภาพจริง, ตัวเลขวัดผล, เดโมผ่านเว็บเซิร์ฟเวอร์จริง)
experiments/     สคริปต์การทดลอง (ดูตารางด้านบน)
results/         CSV, กราฟ, ตาราง, findings.md, pilot_decisions.md
notebooks/       00 ภาพรวมชุดข้อมูล · 01 EDA พิกเซลและ SVD · 02 สาธิตการซ่อนบิตช่วงแรก
demo/            แอปเดโม (app.py = เว็บเซิร์ฟเวอร์, core.py = ตรรกะ, static/index.html = หน้าเว็บ, test_cases.json)
pyproject.toml   ข้อมูลแพ็กเกจ, การตั้งค่า pytest และ ruff
requirements.txt ติดตั้งทุกอย่างในคำสั่งเดียว
```

## ข้อจำกัดที่ควรรู้

- ลายน้ำแบบ Liu–Tan: ถ้าดูแค่ค่า NCC จะเชื่อไม่ได้ เพราะ key เก็บรูปร่างลายน้ำไว้ ภาพต้นฉบับที่ไม่เคยฝังลายน้ำก็ถอดได้ค่า NCC สูง (ดู findings.md)
- รหัสลับหลบตัวสถิติง่ายๆ ได้ แต่ **ตัวตรวจแบบ machine learning ที่ฝึกแล้วยังจับได้** (AUC ≈ 0.99 เมื่อซ่อนเต็มความจุ) เพราะการเปลี่ยน σ₁ ทำให้เกิดขั้นเล็กๆ ที่ขอบบล็อก และรหัสลับไม่ได้เข้ารหัสเนื้อข้อความ
- การซ่อนข้อความไม่ทนการหมุนรูป (แม้ 0.5°) และการเบลอ ส่วนลายน้ำทนการหมุนเล็กน้อยแต่ไม่ทนการเบลอและการเจาะภาพ
