# Math map: where each formula is used in the code

For every piece of mathematics in the project this page says **where it is in the code**, **what goes in and what comes out**, and **which script or demo case shows it**.
All paths are relative to the repository root. Every number below was produced by running the script named next to it.

```
pip install -e .                      # or: set PYTHONPATH=src
python examples/ex7_many_cases.py     # many sample cases, one table per part (about 2 seconds)
python examples/ex1_vectors.py        # ... ex6_hide_text.py: one idea per script
```

Notation: `A` = image matrix (grey levels 0..255), `sigma_1 >= sigma_2 >= ...` = singular values, `delta` = step size, `b` = block size.

## 1. Linear algebra tools

| # | Math | Code | In -> out | See it |
|---|---|---|---|---|
| 1 | Norm `\|v\| = sqrt(v . v)`, dot product, unit vector | `numpy.linalg.norm`, used inside `metrics.ncc` | vectors -> number | `ex1_vectors.py`: `\|(1,1,1)\| = 1.7321` |
| 2 | Cosine / NCC `<w, w*> / (\|w\| \|w*\|)` | `metrics.ncc`, `metrics.ncc_centered` | two matrices -> number in [-1, 1] | `ex1`: NCC(W, W*) = 0.632; `ex4`; watermark cases W1-W6 |
| 3 | Arithmetic mod 2 (bits) | `% 2` in `ecc.encode / decode`, `stego.extract_bit` | bits -> bits | `ex1`: `a + b mod 2 = [0 1 1 0]` |
| 4 | SVD `A = U diag(sigma) V^T`; `sigma_i = sqrt(eigenvalue of A^T A)` | `svd_utils.svd`, `svd_utils.svd_2x2_by_hand` | matrix -> `U, sigma, Vt` | `ex2_svd_2x2.py`: by hand `sigma = [6.7082 2.2361]`, numpy gives the same |
| 5 | Rebuild `A = sum sigma_i u_i v_i^T` | `svd_utils.reconstruct` | `U, sigma, Vt` -> matrix | `ex2`: the sum gives `[[3 0] [4 5]]` back |
| 6 | Energy `\|A\|_F^2 = sum sigma_i^2` | `svd_utils.energy` | `sigma` -> number | `ex2`: `50.0 = 45 + 5` |

## 2. Hiding a message (steganography)

Idea: in every `b x b` block, move the largest singular value `sigma_1` to the middle of an interval whose parity equals the bit to hide.

| # | Math | Code | In -> out | See it |
|---|---|---|---|---|
| 7 | Read a bit: `q = floor(sigma / delta)`, `bit = q mod 2` | `stego.extract_bit`, vectorised `stego.extract_bit_array` | one `sigma` -> 0 or 1 | `ex3_qim_block.py`: `sigma_1 = 113.687`, delta 6, interval 18 -> bit 0 |
| 8 | Write a bit: go to the centre `(q + 1/2) delta` of the nearest interval with the right parity | `stego.embed_value` | `sigma, bit, delta` -> new `sigma` | `ex3`: new `sigma_1 = 117.0` (centre of interval 19) |
| 9 | Cut the image into `b x b` blocks (raster order), 1 bit per block; capacity = `(h/b)(w/b)` bits | `stego.to_blocks`, `from_blocks`, `capacity` | image -> blocks | `ex7` part C: 296 bytes on every 480x320 photo at `b = 8` |
| 10 | Whole block: SVD of each block, change `sigma_1`, rebuild, **round to integers 0..255** | `stego.embed_bits` | image + bits -> new image | `ex3`: rounding moves `sigma_1` from 117 to 117.68, still bit 1 |
| 11 | Closed-loop check with margin `delta/4`: after rounding, read `sigma_1` back exactly as the receiver will and accept only if it is at least `0.25 delta` from both interval edges | `stego.embed_bits` (`margin`, `search`, result fields `weak`, `failed`) | | Failed / weak blocks are reported in the returned `StegoResult` |
| 12 | Reading: SVD of each block, `extract_bit` on `sigma_1` | `stego.extract_bits` | image, `n_bits` -> bits | `ex7` rows A1-A13 ("wrong bits" column) |
| 13 | Secret key: PBKDF2-HMAC-SHA256(key) -> seed -> one offset `u_i` in `[0, 2 delta)` per block shifts that block's interval grid | `stego._key_seed`, `stego._dither` | text key -> offsets | `ex6_hide_text.py` (right key ok, wrong key `no_message`); `ex7` A2-A4: wrong key gives about half the bits wrong (209/440) |
| 14 | Message frame: `length (16 bit) \| CRC (16 bit) \| UTF-8 text`; CRC-16 (CCITT) over length and text | `stego.text_to_bits`, `bits_to_text`, `_crc`, `bytes_to_bits`, `bits_to_bytes` | text <-> bits | status `ok / damaged / no_message` in `ex7` |
| 15 | Capacity of a message: `32 + 8 * bytes` bits (x 7/4 with ECC) | `stego.message_bits_needed`, `text_capacity_bytes` | | `ex7` A14: 360 bytes -> refused, "holds 2400 bits (about 296 bytes)" |
| 16 | End to end | `stego.embed_text`, `stego.extract_text` | text + image -> image; image -> `(text, status)` | `ex6_hide_text.py`; demo cases S1-S14 |

### Error-correcting code Hamming(7,4)

| # | Math | Code | In -> out | See it |
|---|---|---|---|---|
| 17 | Encode `c = d G (mod 2)`, `G = [I4 \| P]`: 4 data bits -> 7 bits | `ecc.encode` | bits -> 1.75x as many bits | `ex5_hamming.py`: `d = [1 0 1 1] -> c = [1 0 1 1 0 1 0]` |
| 18 | Check `s = H r^T (mod 2)`; `s` equals a column of `H` -> that bit is wrong, flip it. `G H^T = 0` | `ecc.decode`, matrices `ecc.G`, `ecc.H` | 7 bits -> 4 bits + number fixed | `ex5`: one flipped bit, syndrome `[0 1 1]` = column 3, `corrected: 1` |
| 19 | Effect on the message | `embed_text(..., ecc=True)`, `extract_text(..., ecc=True, details=True)` | | `ex7` A11 vs A12: same photo, JPEG 60: without ECC `damaged` (15 wrong bits), with ECC `ok` (16 bits fixed). Demo case S13 |

## 3. Watermark (Liu-Tan)

| # | Math | Code | In -> out | See it |
|---|---|---|---|---|
| 20 | Embed: `A = U S V^T`, `D = S + alpha W`, `D = Uw Sw Vw^T`, marked image `A_w = U Sw V^T` | `watermark.embed` | image `A`, logo `W`, `alpha` -> marked image + `WatermarkKey` (`U, Vt, S, Uw, Vwt, alpha, Sw`) | `ex4_watermark.py`: `Sigma_w = [7.2284 2.7284]`; `ex7` B1 |
| 21 | Extract: `D* = Uw diag(sigma*) Vw^T`, `W* = (D* - S) / alpha` | `watermark.extract`, `extract_from_sigma` | received image + key -> logo estimate | `ex4`: `W*` equals `W`; `ex7` B3 (JPEG 75) |
| 22 | Match of the logo: NCC (item 2) | `metrics.ncc` | | `ex7` column NCC |
| 23 | Does the mark exist? `shift = cos(sigma(received) - S, Sw - S)` (our addition, key-free evidence) | `watermark.shift_score`, `shift_from_sigma` | image + key -> number | `ex4`: never marked `NCC = 0.632` but `shift = 0.0`; marked `shift = 1.0`. `ex7` B2: NCC 0.975 yet shift 0.000 |
| 24 | Image quality: `MSE`, `PSNR = 10 log10(255^2 / MSE)` | `metrics.mse`, `rms`, `psnr` | two images -> dB | `ex3` 42.11 dB; `ex6`; every `ex7` row |

Why shift and not NCC: the logo is stored in the key (`Uw`, `Vw`), so NCC stays high even on a photo that was never marked. `ex7` row B2 shows exactly this. The shift score asks whether the singular values moved the way embedding moves them.

## 4. Measuring results

| # | Math | Code | See it |
|---|---|---|---|
| 25 | BER = wrong bits / total bits | `metrics.ber` | `ex7` part C column BER; "wrong bits" column in part A |
| 26 | AUC = P(a marked image scores higher than an unmarked one) | `metrics.auc` | `results/findings.md`, `results/watermark_detection.csv`: marked image vs the same image never marked, alpha 8, noise std 4: NCC AUC 0.30, shift AUC 0.96 |
| 27 | Attacks: Gaussian noise (std in grey levels), JPEG quality, crop (fraction set to 0), blur, rotate | `attacks.apply`, `attacks.gaussian_noise / jpeg / crop_out / blur / rotate` | `ex7` "attack" column (seed 1, so the output repeats exactly) |

## 5. Sample cases: what `ex7_many_cases.py` shows

Output of the run on photo `249061.jpg` (480x320). Message `นัดบ่ายสามที่ตึก 12` (51 bytes), key `kmitl`.

**Part A, steganography**

| Case | Result | What it teaches |
|---|---|---|
| A1, A2 balanced, right key | 0/440 wrong bits, `ok` | embedding and reading work (PSNR 47.90 dB) |
| A3, A4 wrong key / no key | about half the bits wrong, `no_message` | the key shifts every block's grid |
| A5 photo never used | `no_message` | the CRC and length check reject noise |
| A6 JPEG 90, A7 JPEG 50, A8 noise std 4, A10 crop 10% | 0 wrong bits, `ok` | the message survives these attacks |
| A9 robust mode, noise std 8 | `ok` (PSNR 42.04 dB) | bigger blocks and `delta = 64` trade quality for strength |
| A11 vs A12 capacity mode, JPEG 60 | `damaged` without ECC, `ok` with ECC (16 bits fixed) | Hamming(7,4) |
| A13 rotate 0.5 degree | 26/440 wrong, `damaged` | **limit**: blocks no longer line up |
| A14 message of 360 bytes | refused | capacity is checked before embedding |

PSNR is high here because a short message changes only 440 of 2400 blocks. A message that fills the photo gives about 41 dB (report: 40.7 dB average over 400 photos).

**Part B, watermark** (alpha = 16, PSNR 46.92 dB)

| Case | NCC | shift | Reading |
|---|---|---|---|
| B1 no attack | 1.000 | 0.999 | mark found |
| B2 never-marked photo | 0.975 | 0.000 | NCC is fooled, shift is not |
| B3 JPEG 75 | 0.993 | 0.851 | mark found |
| B4 alpha = 2, JPEG 75 | 0.809 | -0.340 | mark too weak to survive |
| B5 rotate 1 degree | 0.984 | 0.728 | unsure |
| B6 blur radius 1 | 0.406 | -0.778 | **limit**: blur defeats this detector |
| B7 noise std 4 | 0.965 | 0.779 | unsure |

**Part C, six photos**: same message, balanced mode, JPEG 90. Every photo carries 296 bytes, PSNR 47.7 to 48.3 dB, BER 0, status `ok`.

Same cases in the browser demo: `demo/test_cases.json` (S1-S14 steganography, W1-W6 watermark). The demo is run with `python demo/app.py`.

## 6. Suggested order for the recording

1. `ex2_svd_2x2.py`: SVD by hand equals numpy (items 4-6).
2. `ex3_qim_block.py`: one bit in one block (items 7-10).
3. `ex5_hamming.py`: one wrong bit found and fixed (items 17-18).
4. `ex4_watermark.py`: Liu-Tan on a 2x2 and the never-marked 3x3 (items 20-23).
5. `ex7_many_cases.py`: all cases at once (sections 2-4 on a real photo).
6. Live demo.

Numbers in this file come from one run on this machine. `ex7` uses fixed seeds, so a rerun prints the same values; PSNR in the last digit can differ if the library versions differ.
