# Behind the Images — SVD-based Digital Watermarking & Steganography

โครงงานวิชา Elementary Differential Equations and Linear Algebra: ใช้ Singular Value Decomposition (SVD) ทำงาน 2 อย่างกับภาพ grayscale

1. **Watermarking** ตามวิธีของ Liu & Tan (2002) คือบวก watermark เข้าไปในค่า singular value ของทั้งภาพ
2. **Steganography** ด้วย QIM คือแบ่งภาพเป็น block ขนาด b×b แล้วเลื่อน singular value ของแต่ละ block ให้ไปอยู่ในช่วง (interval) ที่แทนบิต 0 หรือ 1 (block ละ 1 bit) มีการตรวจซ้ำหลังปัดเศษ pixel (closed-loop พร้อม safety margin Δ/4), key (สร้างตำแหน่งขอบช่วงด้วย PBKDF2) และเปิดใช้ Hamming(7,4) เพื่อแก้บิตที่ผิดได้

ผลทั้งหมดพร้อมตัวเลขอยู่ใน [`results/findings.md`](results/findings.md) ส่วนเหตุผลที่เลือกพารามิเตอร์อยู่ใน [`results/pilot_decisions.md`](results/pilot_decisions.md)

> ชื่อโปรเจกต์คือ **Behind the Images** ส่วน Python package ภายในยังใช้ชื่อ `svdmark` (โฟลเดอร์ `src/svdmark`) จึงต้อง `import svdmark` ในโค้ดและเทสต์

## Dataset

ใช้ภาพ **BSDS500** (Berkeley Segmentation Dataset 500) ทั้ง 500 ภาพ ขนาด 481×321 หรือ 321×481 pixel
ที่มา: Arbeláez, Maire, Fowlkes & Malik, "Contour Detection and Hierarchical Image Segmentation", IEEE TPAMI 33(5), 2011
ดาวน์โหลด: <https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/resources.html>

ภาพทั้ง 500 ภาพ (ประมาณ 40 MB) รวมอยู่ใน repo แล้ว จัดโฟลเดอร์ตามนี้ ลิขสิทธิ์ของภาพเป็นของเจ้าของ dataset ถ้าต้องการดาวน์โหลดชุดข้อมูลต้นฉบับเอง ให้ใช้ลิงก์ด้านบน

```
data/images/train/*.jpg   (200 ภาพ)
data/images/val/*.jpg     (100 ภาพ)
data/images/test/*.jpg    (200 ภาพ)
```

**การแบ่ง split** เราไม่ได้ train model จึงใช้ชื่อ split ของ BSDS500 เป็นเพียงการแบ่งชุดข้อมูลแบบตายตัว

| ชุด | ภาพ | ใช้ทำอะไร |
|---|---|---|
| pilot | `val` 100 ภาพ | เลือกพารามิเตอร์เท่านั้น (b, Δ, σ ตัวที่ใช้, α) |
| eval | `train` + `test` 400 ภาพ | ตัวเลขทุกตัวที่รายงาน ไม่เคยใช้จูนค่า |

**การเตรียมภาพ** (ไฟล์ `src/svdmark/data.py`) แปลงเป็น grayscale ด้วยสูตร 0.299R + 0.587G + 0.114B แล้ว center crop ให้ความกว้างและความสูงหารด้วย 16 ลงตัว ได้ 480×320 (หรือ 320×480) โดยไม่มีการย่อหรือขยายภาพ

## การติดตั้ง

ใช้ Python 3.10 ขึ้นไป รันคำสั่งนี้ในโฟลเดอร์โปรเจกต์

```bash
pip install -r requirements.txt
```

คำสั่งนี้ติดตั้ง package `svdmark` ของโปรเจกต์ (โค้ดใน `src/svdmark` ตั้งค่าไว้ใน `pyproject.toml`) แบบ editable คือแก้โค้ดแล้วมีผลทันทีโดยไม่ต้องติดตั้งใหม่ พร้อม library ที่ต้องใช้ทั้งหมด ทำให้สคริปต์ทดลองและเดโม `import svdmark` ได้จากทุกที่

## การรัน

```bash
pytest                              # รันเทสต์ทั้งหมด (เทสต์ที่ใช้ภาพจริงจะถูกข้ามถ้ายังไม่มีภาพ)
ruff check . && ruff format --check .   # (ไม่บังคับ) ตรวจ code style ต้องติดตั้ง ruff ก่อน: pip install ruff
python experiments/run_all.py       # รันการทดลองทั้งหมดตามลำดับ (~1 ชั่วโมงบนเครื่อง 2 คอร์)
```

`run_all.py` เรียกสคริปต์ตามลำดับนี้ (เรียกทีละขั้นได้ เช่น `python experiments/run_all.py full_stego`) และเก็บ log ไว้ใน `logs/`

| ขั้น | สคริปต์ | ผลลัพธ์ |
|---|---|---|
| 1 | `prepare_data.py` | `results/image_sets.csv`, `results/sigma_eval.csv` |
| 2 | `pilot_stego.py`, `pilot_watermark.py` | `results/pilot_*.csv` (ชุด pilot) |
| 3 | `full_stego.py`, `full_watermark.py` | `results/stego_full.csv`, `results/watermark_full.csv` (ชุด eval) |
| 4 | `analyze_stego.py`, `analyze_watermark.py` | `results/*_summary.csv`, `results/watermark_detection.csv` |
| 5 | `steganalysis.py`, `ml_steganalysis.py` | `results/steganalysis*.csv`, `results/ml_*.csv` (R statistic และ detector แบบ machine learning) |
| 5b | `robustness_extra.py`, `key_strength.py` | ข้อความทั้งก้อนรอดไหม (เปิด/ปิด Hamming, attack เพิ่มเติม: resize, blur, rotate) และความแข็งแรงของ key |
| 6 | `theory_checks.py` | `results/theory_checks.csv` |
| 7 | `make_report_assets.py` | `results/figures/*.png`, `results/tables/*.csv / *.tex` |

ทุกขั้นใช้ seed คงที่ รันซ้ำจะได้ตัวเลขเดิม

## เดโม (web app)

```bash
python demo/app.py          # เปิด http://127.0.0.1:8765 ให้อัตโนมัติ (กด Ctrl+C เพื่อปิด)
```

ใช้เฉพาะ package ใน requirements.txt (web server คือ `http.server` ที่มากับ Python) ทุกปุ่มเรียกโค้ดจริงใน `src/svdmark` ภาพที่อัปโหลดถูกประมวลผลบนเครื่องที่รันเดโม และไม่ถูกบันทึกลงดิสก์

- **Steganography** (หน้าแรก) แบ่งเป็น 3 ส่วน: Sender (เลือกภาพ, ข้อความพร้อมแถบ capacity, key, mode Robust / Balanced / Capacity, Hamming ECC) → Channel (จำลอง attack เช่น JPEG, noise, crop, rotate) → Receiver (Decode ภาพที่เพิ่ง encode หรืออัปโหลดภาพที่ได้รับมา) · พื้นที่ตรงกลางเทียบ Original กับ stego image ได้ทั้งแบบ Slider และ Side by side (หลัง Encode จะสลับเป็น Side by side ให้อัตโนมัติ) พร้อมมุมมอง Difference ×20 และภาพหลัง attack · ดาวน์โหลดเป็น PNG ได้ · คลิกภาพหรือปุ่ม Zoom เพื่อซูมดูทีละ pixel (ภาพในกลุ่มเดียวกันซูมพร้อมกัน)
- **Watermark** ฝัง logo ด้วย α ที่เลือก (พิมพ์ข้อความ หรืออัปโหลดภาพของตัวเอง ซึ่งจะถูกแปลงเป็น black & white ขนาดเท่า Σ ของภาพ) แล้วตรวจภาพที่ฝังเทียบกับภาพต้นฉบับที่ไม่เคยฝัง (เลือก attack ก่อนตรวจได้) เพื่อดูว่าทำไมใช้ NCC อย่างเดียวไม่ได้ และ shift score แยกได้ · พื้นที่ตรงกลางดูภาพหลัง attack และเทียบ logo ที่ดึงออกมาขนาดใหญ่ได้
- **Test cases** มี 20 case ที่ตั้งค่าไว้แล้ว (`demo/test_cases.json`) เลือกภาพที่ใช้ทดสอบได้ (ภาพตาม default, ภาพตัวอย่างอื่น หรืออัปโหลด) กด Run (หรือ Run all) ระบบจะ encode → attack → decode และเทียบกับผลที่คาดไว้โดยอัตโนมัติ จากนั้นผู้ทดสอบกดยืนยันผล ซึ่งบันทึกลง `demo/demo_log.csv` (ดาวน์โหลดได้จากปุ่ม Export CSV)

ฟอนต์ Sarabun และ IBM Plex Mono อยู่ใน `demo/static/fonts` (SIL Open Font License) เดโมจึงใช้งานได้แม้ไม่มีอินเทอร์เน็ต

ภาพตัวอย่างในเดโมมาจาก `data/images` (ถ้าไม่มีโฟลเดอร์นี้ ก็อัปโหลดภาพเองได้)

## ใช้ซ่อนข้อความด้วยโค้ด

```python
from svdmark.data import load_gray
from svdmark import stego

A = load_gray("photo.jpg")                                   # ภาพ grayscale 0..255
r = stego.embed_text(A, "สวัสดี", key="รหัสลับ")              # ค่า default: σ₁, b = 8, Δ = 32
text, status = stego.extract_text(r.image, key="รหัสลับ")     # ("สวัสดี", "ok")

r = stego.embed_text(A, "สวัสดี", key="รหัสลับ", ecc=True)    # เปิด Hamming(7,4): ทนกว่า แต่ capacity เหลือ 4/7
text, status = stego.extract_text(r.image, key="รหัสลับ", ecc=True)
```

สถานะที่ได้จาก `extract_text`
- `ok` ข้อความถูกต้องครบถ้วน (CRC ตรงกัน)
- `no_message` ไม่พบข้อความ (ภาพที่ไม่เคยซ่อนข้อความ หรือใช้ key ผิด)
- `damaged` พบส่วนหัวของข้อความ แต่เนื้อหาเสียหาย (เช่น ภาพถูก compress หรือมี noise)

Capacity: b=8 เก็บได้ 2,400 bits ต่อภาพ 480×320 หักส่วนหัว 32 bits เหลือประมาณ 296 bytes (ตัวอักษรไทยใช้ 3 bytes ต่อตัว จึงได้ประมาณ 98 ตัวอักษร) ถ้าเปิด Hamming จะเหลือ 167 bytes

## โครงสร้าง repo

```
src/svdmark/
  svd_utils.py   SVD, การสร้างเมทริกซ์กลับ, SVD 2×2 แบบคำนวณมือ
  stego.py       Steganography: กฎ QIM, closed-loop, key (PBKDF2), การแปลงข้อความ <-> บิต
  ecc.py         Hamming(7,4): เมทริกซ์ G, H และ syndrome
  watermark.py   Watermark แบบ Liu–Tan และ shift_score (detector ที่เสนอเพิ่ม)
  attacks.py     Attack: Gaussian noise, JPEG, crop
  metrics.py     MSE, RMS, PSNR, NCC, BER, AUC (ใช้วัดว่า detector แยกภาพได้ดีแค่ไหน)
  data.py        โหลดภาพ, แปลง grayscale, crop, ชุด pilot / eval
data/images/      ภาพ BSDS500 ทั้ง 500 ภาพ (train / val / test)
examples/        สคริปต์ตัวอย่างที่คำนวณซ้ำตัวอย่างมือในรายงานบทที่ 4 ด้วยโค้ดของโปรเจกต์ (ดู examples/README.md)
tests/           เทสต์ (ตัวอย่างคำนวณมือ, encode แล้ว decode กลับ, ภาพจริง, ตัวเลขผลการทดลอง, เดโมผ่าน web server จริง)
experiments/     สคริปต์การทดลอง (ดูตารางด้านบน)
results/         CSV, กราฟ, ตาราง, findings.md, pilot_decisions.md
report/          รายงานฉบับสมบูรณ์ (report.docx และ report.pdf)
notebooks/       00 ภาพรวม dataset · 01 EDA ของ pixel และ SVD · 02 สาธิตการซ่อนบิตช่วงแรก
demo/            เดโม (app.py = web server, core.py = logic, static/index.html = หน้าเว็บ, test_cases.json)
pyproject.toml   ข้อมูล package, การตั้งค่า pytest และ ruff
requirements.txt ติดตั้งทุกอย่างในคำสั่งเดียว
```

## ข้อจำกัดที่ควรรู้

- Watermark แบบ Liu–Tan: ดู NCC อย่างเดียวเชื่อถือไม่ได้ เพราะ key เก็บรูปร่างของ watermark ไว้ ภาพต้นฉบับที่ไม่เคยฝัง watermark ก็ดึง logo ออกมาได้ NCC สูง (ดู findings.md)
- Key ช่วยให้หลบ statistical test ง่ายๆ ได้ แต่ **detector แบบ machine learning ที่ผ่านการ train แล้วยังจับได้** (AUC ≈ 0.99 เมื่อซ่อนเต็ม capacity) เพราะการเปลี่ยน σ₁ ทำให้เกิดขั้นเล็กๆ ที่ขอบ block และ key ไม่ได้เข้ารหัสเนื้อข้อความ
- Steganography ไม่ทนต่อการ rotate (แม้ 0.5°) และ blur ส่วน watermark ทนการ rotate เล็กน้อยได้ แต่ไม่ทนต่อ blur และ crop
