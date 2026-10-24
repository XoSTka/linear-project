# แผนที่คณิตศาสตร์ → โค้ด

หน้านี้บอกว่าสูตรแต่ละตัวในโปรเจกต์ **อยู่ในโค้ดตรงไหน** · **รับอะไรเข้าไปและได้อะไรออกมา** · **รันสคริปต์หรือเดโมไหนถึงจะเห็นผล**
path ทั้งหมดนับจากโฟลเดอร์หลักของ repo และตัวเลขทุกตัวมาจากการรันสคริปต์ที่ระบุไว้ข้างๆ

```
pip install -e .                      # หรือ set PYTHONPATH=src
python examples/ex7_many_cases.py     # รันหลายเคสรวด พิมพ์ตารางผล (ใช้เวลาประมาณ 2 วินาที)
python examples/ex1_vectors.py        # ... ถึง ex6_hide_text.py: สคริปต์ละหนึ่งแนวคิด
```

**สัญลักษณ์ที่ใช้**
- `A` = เมทริกซ์ของรูป แต่ละช่องคือความสว่างของ 1 พิกเซล ค่า 0 (ดำ) ถึง 255 (ขาว)
- `sigma_1 >= sigma_2 >= ...` (σ อ่านว่า ซิกมา) = singular value ของเมทริกซ์ คือตัวเลขที่บอกว่าแต่ละ "ชั้น" ของเมทริกซ์แรงแค่ไหน เรียงจากมากไปน้อย
- `delta` (Δ เดลตา) = ขนาดช่วงที่ใช้ตอนซ่อน 1 bit ยิ่งกว้างยิ่งทนการรบกวน แต่ยิ่งแก้รูปมาก
- `b` = ขนาด block รูปถูกตัดเป็นสี่เหลี่ยม `b × b` แต่ละอันซ่อนได้ 1 bit
- `S` = เมทริกซ์ทแยงมุมที่มี σ เรียงอยู่ · `W` = โลโก้ลายน้ำ · `alpha` (α แอลฟา) = ความเข้มของลายน้ำที่ผสมเข้าไป

## 1. เครื่องมือพีชคณิตเชิงเส้น

| # | คณิตศาสตร์ | โค้ด | รับ → ได้ | ดูผลได้ที่ |
|---|---|---|---|---|
| 1 | Norm (ความยาวเวกเตอร์) `\|v\| = sqrt(v . v)`, dot product, unit vector | `numpy.linalg.norm` ใช้ใน `metrics.ncc` | เวกเตอร์ → ตัวเลข | `ex1_vectors.py`: `\|(1,1,1)\| = 1.7321` |
| 2 | Cosine / NCC `<w, w*> / (\|w\| \|w*\|)` (1 = ชี้ทางเดียวกัน, 0 = ไม่เกี่ยวกัน) | `metrics.ncc`, `metrics.ncc_centered` | เมทริกซ์ 2 ตัว → ตัวเลขใน [-1, 1] | `ex1`: NCC(W, W*) = 0.632; `ex4`; เคสลายน้ำ W1–W6 |
| 3 | เลขคณิต mod 2 (1+1 = 0) ใช้กับ bit | `% 2` ใน `ecc.encode / decode`, `stego.extract_bit` | bit → bit | `ex1`: `a + b mod 2 = [0 1 1 0]` |
| 4 | SVD `A = U diag(sigma) V^T` โดย `sigma_i = sqrt(eigenvalue ของ A^T A)` | `svd_utils.svd`, `svd_utils.svd_2x2_by_hand` | เมทริกซ์ → `U, sigma, Vt` | `ex2_svd_2x2.py`: คำนวณมือได้ `sigma = [6.7082 2.2361]` numpy ได้เท่ากัน |
| 5 | ประกอบกลับ `A = sum sigma_i u_i v_i^T` | `svd_utils.reconstruct` | `U, sigma, Vt` → เมทริกซ์ | `ex2`: รวมแล้วได้ `[[3 0] [4 5]]` กลับมา |
| 6 | Energy `\|A\|_F^2 = sum sigma_i^2` (ผลรวมกำลังสองของทุกช่อง) | `svd_utils.energy` | `sigma` → ตัวเลข | `ex2`: `50.0 = 45 + 5` |

## 2. ซ่อนข้อความ (steganography)

แนวคิด: ในแต่ละ block ขนาด `b × b` ขยับ `sigma_1` (ตัวใหญ่สุด) ไปอยู่กลางช่วงที่ parity (คู่/คี่) ตรงกับ bit ที่จะซ่อน

| # | คณิตศาสตร์ | โค้ด | รับ → ได้ | ดูผลได้ที่ |
|---|---|---|---|---|
| 7 | อ่าน bit: `q = floor(sigma / delta)`, `bit = q mod 2` | `stego.extract_bit` และแบบ vectorised `stego.extract_bit_array` | `sigma` 1 ค่า → 0 หรือ 1 | `ex3_qim_block.py`: `sigma_1 = 113.687`, delta 6, ช่วงที่ 18 → bit 0 |
| 8 | เขียน bit: ขยับไปกลางช่วง `(q + 1/2) delta` ของช่วงที่ใกล้ที่สุดซึ่ง parity ตรง | `stego.embed_value` | `sigma, bit, delta` → `sigma` ใหม่ | `ex3`: `sigma_1` ใหม่ = `117.0` (กลางช่วงที่ 19) |
| 9 | ตัดรูปเป็น block `b × b` เรียงแบบอ่านหนังสือ 1 block = 1 bit; ความจุ = `(h/b)(w/b)` bit | `stego.to_blocks`, `from_blocks`, `capacity` | รูป → block | `ex7` ส่วน C: 296 bytes ทุกรูปขนาด 480×320 ที่ `b = 8` |
| 10 | ทำทั้ง block: SVD ของ block → เปลี่ยน `sigma_1` → ประกอบกลับ → **ปัดเป็นเลขจำนวนเต็ม 0..255** | `stego.embed_bits` | รูป + bit → รูปใหม่ | `ex3`: หลังปัดเศษ `sigma_1` เลื่อนจาก 117 เป็น 117.68 ยังอ่านได้ bit 1 |
| 11 | Closed-loop check ที่ margin `delta/4`: หลังปัดเศษ อ่าน `sigma_1` กลับแบบเดียวกับผู้รับ และยอมรับก็ต่อเมื่อห่างจากขอบช่วงทั้งสองข้างอย่างน้อย `0.25 delta` | `stego.embed_bits` (พารามิเตอร์ `margin`, `search`; ผลลัพธ์ `weak`, `failed`) | | block ที่ฝังไม่ได้หรือไม่มั่นคงจะถูกรายงานใน `StegoResult` |
| 12 | อ่านกลับ: SVD ของแต่ละ block แล้ว `extract_bit` กับ `sigma_1` | `stego.extract_bits` | รูป, `n_bits` → bit | `ex7` แถว A1–A13 (คอลัมน์ "wrong bits") |
| 13 | Secret key: PBKDF2-HMAC-SHA256(key) → seed → ค่าเลื่อน `u_i` ใน `[0, 2 delta)` ของแต่ละ block เลื่อนตารางช่วงของ block นั้น | `stego._key_seed`, `stego._dither` | key ที่เป็นข้อความ → ค่าเลื่อน | `ex6_hide_text.py` (key ถูกอ่านได้ key ผิดได้ `no_message`); `ex7` A2–A4: key ผิดทำให้ bit ผิดประมาณครึ่งหนึ่ง (209/440) |
| 14 | Frame ของข้อความ: `ความยาว (16 bit) \| CRC (16 bit) \| ข้อความ UTF-8` โดย CRC-16 (CCITT) คำนวณจากความยาวและข้อความ | `stego.text_to_bits`, `bits_to_text`, `_crc`, `bytes_to_bits`, `bits_to_bytes` | ข้อความ ↔ bit | สถานะ `ok / damaged / no_message` ใน `ex7` |
| 15 | จำนวน bit ที่ข้อความต้องใช้: `32 + 8 × bytes` (คูณ 7/4 ถ้าเปิด ECC) | `stego.message_bits_needed`, `text_capacity_bytes` | | `ex7` A14: ข้อความ 360 bytes ถูกปฏิเสธ "ใส่ได้ 2400 bit (ประมาณ 296 bytes)" |
| 16 | ทั้งกระบวนการ | `stego.embed_text`, `stego.extract_text` | ข้อความ + รูป → รูป; รูป → `(ข้อความ, สถานะ)` | `ex6_hide_text.py`; เคสเดโม S1–S14 |

### Error-correcting code: Hamming(7,4)

CRC บอกได้แค่ว่ามี bit ผิด แต่แก้ไม่ได้ Hamming(7,4) เติม bit ตรวจ 3 ตัวต่อทุก 4 bit ข้อมูล ทำให้แก้ bit ที่ผิด 1 ตัวต่อ 7 bit ได้

| # | คณิตศาสตร์ | โค้ด | รับ → ได้ | ดูผลได้ที่ |
|---|---|---|---|---|
| 17 | Encode `c = d G (mod 2)`, `G = [I4 \| P]`: ข้อมูล 4 bit → 7 bit | `ecc.encode` | bit → bit (จำนวน 1.75 เท่า) | `ex5_hamming.py`: `d = [1 0 1 1] → c = [1 0 1 1 0 1 0]` |
| 18 | ตรวจ `s = H r^T (mod 2)` ถ้า `s` เท่ากับคอลัมน์ใดของ `H` แปลว่า bit ตำแหน่งนั้นผิด ให้พลิกกลับ และ `G H^T = 0` | `ecc.decode`, เมทริกซ์ `ecc.G`, `ecc.H` | 7 bit → 4 bit + จำนวนที่แก้ | `ex5`: พลิก 1 bit, syndrome `[0 1 1]` = คอลัมน์ 3, `corrected: 1` |
| 19 | ผลต่อข้อความจริง | `embed_text(..., ecc=True)`, `extract_text(..., ecc=True, details=True)` | | `ex7` A11 เทียบ A12: รูปเดียวกัน JPEG 60: ไม่มี ECC ได้ `damaged` (ผิด 15 bit) มี ECC ได้ `ok` (แก้ 16 bit) และเคสเดโม S13 |

## 3. ลายน้ำ (Liu–Tan)

| # | คณิตศาสตร์ | โค้ด | รับ → ได้ | ดูผลได้ที่ |
|---|---|---|---|---|
| 20 | ฝัง: `A = U S V^T`, `D = S + alpha W`, `D = Uw Sw Vw^T`, รูปที่มีลายน้ำ `A_w = U Sw V^T` | `watermark.embed` | รูป `A`, โลโก้ `W`, `alpha` → รูปที่มีลายน้ำ + `WatermarkKey` (`U, Vt, S, Uw, Vwt, alpha, Sw`) | `ex4_watermark.py`: `Sigma_w = [7.2284 2.7284]`; `ex7` B1 |
| 21 | ถอด: `D* = Uw diag(sigma*) Vw^T`, `W* = (D* - S) / alpha` | `watermark.extract`, `extract_from_sigma` | รูปที่ได้รับ + key → โลโก้ที่ประมาณได้ | `ex4`: `W*` เท่ากับ `W`; `ex7` B3 (JPEG 75) |
| 22 | วัดว่าโลโก้ตรงแค่ไหน: NCC (ข้อ 2) | `metrics.ncc` | | `ex7` คอลัมน์ NCC |
| 23 | ลายน้ำมีอยู่จริงไหม? `shift = cos(sigma(รูปที่ได้รับ) - S, Sw - S)` (ส่วนที่ทีมเพิ่มเอง ใช้เป็นหลักฐานโดยไม่ต้องดูโลโก้) | `watermark.shift_score`, `shift_from_sigma` | รูป + key → ตัวเลข | `ex4`: รูปไม่เคยฝัง `NCC = 0.632` แต่ `shift = 0.0`; รูปที่ฝัง `shift = 1.0`. `ex7` B2: NCC 0.975 แต่ shift 0.000 |
| 24 | คุณภาพรูป: `MSE`, `PSNR = 10 log10(255^2 / MSE)` (หน่วย dB ยิ่งสูงยิ่งใกล้ต้นฉบับ) | `metrics.mse`, `rms`, `psnr` | รูป 2 รูป → dB | `ex3` 42.11 dB; `ex6`; ทุกแถวของ `ex7` |

**ทำไมใช้ shift ไม่ใช้ NCC อย่างเดียว:** โครงของโลโก้ถูกเก็บอยู่ใน key (`Uw`, `Vw`) NCC จึงสูงแม้กับรูปที่ไม่เคยฝังลายน้ำ แถว B2 ใน `ex7` แสดงตรงนี้ ส่วน shift ถามว่า σ ของรูปขยับไปทางเดียวกับที่การฝังขยับหรือไม่

## 4. การวัดผล

| # | คณิตศาสตร์ | โค้ด | ดูผลได้ที่ |
|---|---|---|---|
| 25 | BER = bit ที่ผิด ÷ bit ทั้งหมด | `metrics.ber` | `ex7` ส่วน C คอลัมน์ BER; คอลัมน์ "wrong bits" ในส่วน A |
| 26 | AUC = ความน่าจะเป็นที่รูปมีลายน้ำได้คะแนนสูงกว่ารูปไม่มี (0.5 = แยกไม่ได้, 1 = แยกได้หมด) | `metrics.auc` | `results/findings.md`, `results/watermark_detection.csv`: รูปที่ฝังเทียบกับรูปเดียวกันที่ไม่เคยฝัง, alpha 8, noise std 4: NCC AUC 0.30 เทียบกับ shift AUC 0.96 |
| 27 | Attack: Gaussian noise (std เป็นระดับสีเทา), JPEG quality, crop (ส่วนที่ตัดเป็น 0), blur, rotate | `attacks.apply`, `attacks.gaussian_noise / jpeg / crop_out / blur / rotate` | `ex7` คอลัมน์ "attack" (seed 1 จึงรันซ้ำได้ผลเดิม) |

## 5. ตัวอย่างเคสจาก `ex7_many_cases.py`

ผลการรันกับรูป `249061.jpg` (480×320) ข้อความ `นัดบ่ายสามที่ตึก 12` (51 bytes) key `kmitl`

**ส่วน A ซ่อนข้อความ**

| เคส | ผล | ได้เรียนรู้อะไร |
|---|---|---|
| A1, A2 mode balanced, key ถูก | ผิด 0/440 bit, `ok` | ฝังและอ่านกลับได้ (PSNR 47.90 dB) |
| A3, A4 key ผิด / ไม่ใส่ key | ผิดประมาณครึ่งหนึ่ง, `no_message` | key เลื่อนตารางช่วงของทุก block |
| A5 รูปที่ไม่เคยซ่อนข้อความ | `no_message` | CRC และการเช็กความยาวปฏิเสธข้อมูลมั่ว |
| A6 JPEG 90, A7 JPEG 50, A8 noise std 4, A10 crop 10% | ผิด 0 bit, `ok` | ข้อความรอดจาก attack เหล่านี้ |
| A9 mode robust, noise std 8 | `ok` (PSNR 42.04 dB) | block ใหญ่และ `delta = 64` แลกคุณภาพกับความทน |
| A11 เทียบ A12 mode capacity, JPEG 60 | ไม่มี ECC ได้ `damaged`, มี ECC ได้ `ok` (แก้ 16 bit) | Hamming(7,4) |
| A13 หมุน 0.5 องศา | ผิด 26/440, `damaged` | **ข้อจำกัด:** block ไม่ตรงตำแหน่งเดิมอีกต่อไป |
| A14 ข้อความ 360 bytes | ถูกปฏิเสธ | ตรวจความจุก่อนฝัง |

PSNR สูงเพราะข้อความสั้นแก้แค่ 440 จาก 2400 block ถ้าข้อความเต็มรูปจะได้ราว 41 dB (รายงาน: เฉลี่ย 40.7 dB จาก 400 รูป)

**ส่วน B ลายน้ำ** (alpha = 16, PSNR 46.92 dB)

| เคส | NCC | shift | อ่านผล |
|---|---|---|---|
| B1 ไม่มี attack | 1.000 | 0.999 | พบลายน้ำ |
| B2 รูปไม่เคยฝัง | 0.975 | 0.000 | NCC โดนหลอก แต่ shift ไม่โดน |
| B3 JPEG 75 | 0.993 | 0.851 | พบลายน้ำ |
| B4 alpha = 2, JPEG 75 | 0.809 | -0.340 | ลายน้ำเบาเกินไป ไม่รอด |
| B5 หมุน 1 องศา | 0.984 | 0.728 | ไม่แน่ใจ |
| B6 blur รัศมี 1 | 0.406 | -0.778 | **ข้อจำกัด:** blur ทำให้ตัวตรวจนี้พลาด |
| B7 noise std 4 | 0.965 | 0.779 | ไม่แน่ใจ |

**ส่วน C 6 รูป:** ข้อความเดียวกัน mode balanced, JPEG 90 ทุกรูปจุได้ 296 bytes, PSNR 47.7–48.3 dB, BER 0, สถานะ `ok`

เคสชุดเดียวกันในเว็บเดโม: `demo/test_cases.json` (S1–S14 ซ่อนข้อความ, W1–W6 ลายน้ำ) รันเดโมด้วย `python demo/app.py`

## 6. ลำดับที่แนะนำตอนอัดคลิป

เปิดไฟล์โค้ดจริงใน `src/svdmark/` ที่คอลัมน์ "โค้ด" บอก อธิบายฟังก์ชัน แล้วรันสคริปต์ที่คอลัมน์ "ดูผลได้ที่" บอก

1. `ex2_svd_2x2.py`: SVD คำนวณมือเท่ากับ numpy (ข้อ 4–6)
2. `ex3_qim_block.py`: 1 bit ใน 1 block (ข้อ 7–10)
3. `ex5_hamming.py`: bit ผิด 1 ตัวถูกหาเจอและแก้ (ข้อ 17–18)
4. `ex4_watermark.py`: Liu–Tan บนเมทริกซ์ 2×2 และเคส 3×3 ที่ไม่เคยฝัง (ข้อ 20–23)
5. `ex7_many_cases.py` หรือ `notebooks/03_math_and_cases.ipynb`: ทุกเคสพร้อมกันบนรูปจริง (หัวข้อ 2–4)
6. เดโมสด

ตัวเลขในไฟล์นี้มาจากการรันครั้งเดียวบนเครื่องผู้เขียน `ex7` ใช้ seed คงที่ รันซ้ำได้ค่าเดิม แต่ทศนิยมตัวท้ายของ PSNR อาจต่างได้ถ้าเวอร์ชันไลบรารีต่างกัน
