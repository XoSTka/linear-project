# Findings (evaluation set: 400 images, 480x320 / 320x480 grayscale)

Source of every number: the CSV files in `results/` (`watermark_full`, `watermark_summary`, `watermark_detection`,
`stego_full`, `stego_summary`, `theory_checks`, `steganalysis_summary`).
* **Images.** BSDS500, all 500 images. Parameters were chosen on the 100 `val` images only (the pilot set,
  `pilot_decisions.md`); every number below comes from the other 400 (`train` + `test`), which were never used for tuning.
* Attack levels were fixed in `attacks.py` before any result was seen. All runs use fixed seeds.

## Watermarking (Liu-Tan), random binary mark 320x320
* **Quality** after saving as 8-bit: mean PSNR 78.1 / 59.6 / 49.3 / 44.1 / 40.3 / 34.9 dB for alpha = 2 / 4 / 8 / 12 / 16 / 24.
  Share of images >= 40 dB: 100 / 100 / 100 / 95 / 58 / 0 %. alpha = 16 is the edge of the 40 dB target, not safely inside it.
* **NCC alone is not evidence.** Extracting with the key from the SAME image never watermarked gives
  NCC 0.995 / 0.991 / 0.981 / 0.970 / 0.960 / 0.939 (alpha 2 ... 24) and BER 0.15-1.0 %.
  Reason: the off-diagonal part of the mark is stored in the key (Uw, Vw), only the diagonal part (320 of
  102,400 entries) moves the image's singular values. From a DIFFERENT image NCC is only 0.05-0.38.
  Under attack, NCC cannot separate a marked image from the same image never marked
  (AUC 0.30 for alpha 8 at noise 4; 0.24 at JPEG 90; 0.24 for alpha 12 at noise 8 — below 0.5 because the
  never-marked image can score higher).
* **Our singular-value shift score** (cosine of sigma(received) - S with Sw - S; not part of Liu-Tan) separates them:
  AUC 0.96 (alpha 8, noise 4), 0.91 (alpha 8, JPEG 90), 0.88 (alpha 12, noise 8), >= 0.98 for alpha >= 12 under every JPEG level.
  It is 0 for every never-marked image without attack, but an attack alone moves sigma, so a never-marked attacked image
  scores 0.5-0.75 (alpha 8, noise) — the score is a relative test, not an absolute one.
* **Both tests are needed.** NCC tells the marked image from a DIFFERENT image (AUC 1.0 except crop); the shift score
  does not always (alpha 2 under JPEG 75 / 50: AUC 0.30 / 0.05).
* **alpha = 2 is too weak:** after any attack both tests are near chance (AUC 0.42-0.64).
* **Crop** (5-25 % removed): both tests weak (shift AUC 0.59-0.86 at alpha 8; NCC AUC 0.54-0.55). The scheme is not crop-robust.

## Steganography (QIM on sigma, closed-loop checked with a safety margin), full-capacity random bits
* **Closed loop with safety margin.** A candidate sigma is accepted only if, after rebuilding the block and rounding to
  integers 0..255, it reads back the right bit AND sits at least delta/4 from both edges of its interval.
  (Added after the demo found blocks clipped at 255 whose sigma landed right at an edge, so even JPEG 95 flipped them.)
  Compared with the plain check, BER at delta = 4b, b = 8 fell from 0.13 to 0.06 % (noise 4) and from 0.16 to 0.08 % (JPEG 75)
  at the same PSNR.
* **Closed-loop failures.** sigma_1 never fails (0 blocks in 400 images, every b and delta tested);
  sigma_2 fails in 0.02-0.22 % of blocks (those bits read wrong, so sigma_2 has BER 0.02-0.22 % even without attack).
* **PSNR depends on delta / b only:** delta = 2b / 3b / 4b / 6b / 8b → 46.5 / 43.1 / 40.7 / 37.3 / 34.8 dB (same for b = 4, 8, 16).
* **Chosen setting delta = 4b, sigma_1** (40.7 dB; 99.0-99.3 % of images >= 40 dB, worst image 39.1 dB). Mean BER (%):

| b | bits/image | noise s=4 | noise s=8 | JPEG 75 | JPEG 50 | crop 10 % | crop 25 % |
|---|---|---|---|---|---|---|---|
| 4 | 9600 | 5.10 | 32.17 | 0.59 | 8.38 | 5.15 | 12.49 |
| 8 | 2400 | 0.06 | 5.86 | 0.08 | 0.28 | 5.87 | 12.50 |
| 16 | 600 | 0.02 | 0.63 | 0.03 | 0.11 | 6.78 | 13.36 |

  No attack, JPEG 95, noise s = 1: BER 0 (or < 0.01 %) everywhere. Crop BER is about half the removed area for every b
  (lost blocks read as random bits). At equal quality, larger blocks resist noise and JPEG much better but carry
  4x / 16x fewer bits.
* sigma_2 at delta = 4b is clearly worse (b = 8: noise 4 → 0.59 %, JPEG 75 → 1.25 %; b = 4: 8.5 % and 25.5 %).
* **Text frame.** 16-bit length | CRC-16 over length + payload (start value 0xFFFF) | UTF-8 payload.
  Optional error correction: the whole frame is coded with Hamming(7,4) (`ecc.py`; capacity x 4/7, e.g. 296 → 167 bytes at b = 8).
  Never-used images (400 x 3 settings) give `no_message` or `damaged`, never `ok`.
  With the default setting (sigma_1, b = 8, delta = 32) a 245-byte Thai/English message round-trips on all 100 images
  tested; the wrong key and no key both give `no_message` (100 / 100).
  *Fixed during review:* the first version computed the CRC over the payload only, starting from 0, so an all-zero
  header (common in flat photo regions) decoded as a valid empty message; in the earlier 150-image sample 51 never-used images (34 %) reported `ok` at b = 8.
* **A whole message needs every bit right** (one wrong bit → CRC fails → `damaged`). `robustness_extra.csv`: a 34-byte Thai
  message with the secret key, 100 evaluation images, % read back exactly (no ECC → with Hamming(7,4)):

| attack | b = 16 | b = 8 | b = 4 |
|---|---|---|---|
| JPEG 75 | 97 → 100 | 99 → 99 | 60 → 97 |
| JPEG 60 | 93 → 97 | 93 → 97 | 2 → 43 |
| JPEG 50 | 92 → 96 | 90 → 96 | 0 → 2 |
| noise s = 4 | 93 → 98 | 86 → 97 | 0 → 5 |
| noise s = 8 | 69 → 85 | 0 → 4 | 0 → 0 |
| crop 10 % | 0 → 0 | 100 → 100 | 100 → 100 |
| resize to 75 % and back | 78 → 87 | 81 → 85 | 60 → 70 |
| resize to 50 % and back | 47 → 61 | 45 → 50 | 34 → 41 |
| blur radius 0.5 / 1 | 78 → 85 / 5 → 9 | 70 → 73 / 17 → 16 | 41 → 55 / 8 → 15 |
| median 3x3 | 6 → 7 | 30 → 27 | 17 → 28 |
| rotate 0.5° or 1° | 0-1 | 0 | 0 |

  Error correction helps most where errors are rare but not zero (small blocks under JPEG 75: 60 → 97 %).
  It cannot help when errors are dense (blur, rotation, the cut-out region). Crop depends on WHERE the message is:
  a short message sits in the top rows (raster order) and escapes a centred cut at b = 4 / 8, but fills most of the
  image at b = 16. Spreading the coded bits over the whole image was tried and made crop worse, so it was dropped.
  **Rotation by 0.5° destroys every message**: the 8x8 grid no longer lines up with the blocks. Smoothing (blur,
  median, resize) changes block brightness and hurts too.

## Theory vs experiment
* ||Aw - A||_F = ||Sw - S||_F: max relative difference 6.9e-14 over 400 images (rounding error only).
* Weyl: max over blocks of max_i |d sigma_i| / ||E||_2 = 0.997 <= 1.
* sigma_1 drift under Gaussian noise has rms = noise std (0.997 / 2.00 / 4.00 / 8.02 for s = 1 / 2 / 4 / 8),
  so BER ≈ 2 Q(delta / 2s). Predicted vs measured BER (%), b = 8:
  delta 16, s 4: 4.55 vs 4.67;  delta 32, s 8: 4.55 vs 4.44;  delta 24, s 8: 13.36 vs 13.49;  delta 16, s 8: 31.73 vs 31.60.
* Rounding rule: rounding moves sigma_1 by at most 1.3 here (bound b/2). No flips for delta >= b in any tested case;
  delta = b/4 at b = 4 flips 8.4 %. The only sigma_1 closed-loop failures in the pilot are at delta < b (b = 16, delta = 8).
* sigma_1 holds 88.9 % of an image's energy on average (minimum 59.6 %).

## Watermark under extra attacks (`robustness_extra_wm_summary.csv`, 100 images, AUC marked vs same image never marked)
* **Small rotations are fine** (global SVD barely changes): rotate 1°, shift-score AUC 0.97 (alpha 8) / 1.00 (alpha 16).
* **Smoothing hurts**: blur radius 1 → shift AUC 0.57 / 0.80; resize to 50 % and back → 0.64 / 0.89; median 3x3 → 0.65 / 0.95.
  Smoothing lowers all singular values, so both marked and never-marked images get a NEGATIVE shift score: the score
  still ranks them (AUC), but a fixed threshold (like the demo's 0.8 / 0.3) would call the marked image "no evidence".

## Secret key strength (`key_strength.csv`)
* **First version:** seed = CRC32(key) → only 2^32 different grids. An attacker who knows the method loops over all
  seeds directly: about 53,000 seeds per second on one core → about 23 hours (about 3 hours on 8 cores) to try them all,
  each candidate checked with the header and CRC. **Fixed during review.**
* **Now:** seed = PBKDF2-HMAC-SHA256(key, fixed salt, 200,000 rounds) → 256-bit seed; the attacker must guess the key and
  every guess costs about 0.05-0.07 s. Every 8-letter lowercase key: about 45 years on 8 cores; every 10-character
  letters + digits key: about 10^8 years. A common word is still found quickly (the real key 'kmitl' in a 50-word list: 2.7 s).
  The key hides where the bits are; the message itself is not encrypted.

## Statistical detectability (phase-concentration statistic R on sigma / delta)
AUC = P(stego image scores higher than its original). An AUC far **below** 0.5 is also detection (the stego images score
systematically lower), so we also report the separability max(AUC, 1 - AUC): 0.5 = cannot tell apart, 1 = perfect.
* **Plain scheme:** AUC 1.000 even when delta is unknown; the values pile up at the interval centres.
* **With the secret key, sigma_1:** separability 0.57-0.73 (AUC 0.27-0.43), with unchanged PSNR and BER.
* **With the secret key, sigma_2:** separability 0.87-0.94 when delta is known (AUC 0.06-0.13). Natural sigma_2 values
  are slightly concentrated; the key makes them *too* uniform, and that is itself detectable. Scanning delta blindly
  weakens this (separability 0.52-0.75). So the key hides sigma_1 against this statistic, sigma_2 not.

## Trained detector (machine learning, `ml_steganalysis.csv`)
Logistic regression on 11 pixel features (no key needed), trained on the 100 pilot images (original + modified),
tested on the 400 evaluation images. AUC on the test images:

| modified image | AUC | accuracy | blockiness at grid 8 alone |
|---|---|---|---|
| stego, no key, full capacity | 1.00 | 1.00 | 0.91 |
| stego, secret key, full capacity (delta 32) | 0.99 | 0.95 | 0.91 |
| stego, secret key, full capacity, delta 24 | 0.96 | 0.89 | 0.84 |
| stego, secret key, full capacity, delta 16 | 0.86 | 0.76 | 0.74 |
| stego, secret key, short message (16 % of capacity) | 0.79 | 0.70 | 0.69 |
| watermark alpha 8 | 0.69 | 0.63 | 0.55 |
| watermark alpha 16 | 0.85 | 0.77 | 0.59 |

* **The secret key does NOT hide the message from a trained detector.** The strongest clue is *blockiness*: changing
  sigma_1 adds d * u1 v1^T, and for smooth blocks u1 and v1 are nearly flat vectors, so the whole 8x8 block shifts its
  brightness by almost the same amount and a small step appears at every block border. The key randomises *where in
  the interval* sigma_1 lands, not this step.
* Detectability falls with smaller changes (delta 32 → 16: AUC 0.99 → 0.86) and with shorter messages (0.79), at the
  cost of robustness / capacity. The watermark (global SVD, no blocks) is harder to spot (0.69 at alpha 8).
* This is a simple detector with 11 hand-made features; a deep network (e.g. SRNet) would likely do at least as well.
  The honest claim is: the key defeats the simple statistic R, not a trained detector.
