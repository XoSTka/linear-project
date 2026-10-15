# Findings from the full run (150 images, 480x320 / 320x480 grayscale)

Source of every number: the CSV files in `results/` (`watermark_full`, `stego_full`, `theory_checks`, `steganalysis`).
Attack levels were fixed in `attacks.py` before any result was seen.  Pilot (30 `val` images) only chose the grid.

## Watermarking (Liu-Tan), random binary mark 320x320
* Quality after saving as 8-bit: mean PSNR 77.5 / 59.4 / 49.2 / 43.9 / 40.2 / 34.8 dB for alpha = 2 / 4 / 8 / 12 / 16 / 24.
  Share of images >= 40 dB: 100 / 100 / 100 / 94 / 57 / 1 %.  alpha = 16 is the edge of the 40 dB target, not safely inside it.
* NCC and BER of the extracted mark are dominated by the key: extracting from the same image NEVER watermarked gives
  NCC 0.96-0.98 (alpha 8-16) and BER 0.2 %.  Under attack, NCC cannot separate marked from never-marked images
  (AUC 0.31 for alpha = 8 at noise sigma = 4; 0.27 at JPEG Q90; 0.23 for alpha = 12 at noise sigma = 8).
* Our singular-value shift score (cosine of sigma(received) - S with Sw - S) separates them:
  AUC 0.95 (alpha 8, noise 4), 0.90 (alpha 8, JPEG 90), 0.86 (alpha 12, noise 8), >= 0.98 for alpha >= 12 under JPEG.
  NCC still tells the marked image from a DIFFERENT image (AUC 1.0 except crop), so both tests are needed.
* Crop (5-25 % removed): both tests weak (shift AUC 0.59-0.86 at alpha 8; NCC ~0.55).  The scheme is not crop-robust.

## Steganography (QIM on sigma, closed-loop checked), full-capacity random bits
* sigma_1 never fails the closed-loop check (0 of 150 images); sigma_2 fails in 0.02-0.25 % of blocks; sigma_3.. are unusable (pilot).
* PSNR depends on delta/b only: delta = 2b / 3b / 4b / 6b / 8b -> 46.5 / 43.2 / 40.8 / 37.3 / 34.8 dB.
* At delta = 4b (40.8 dB), sigma_1, mean BER (%):

| b | bits/image | noise s=4 | JPEG 75 | JPEG 50 | crop 10 % |
|---|---|---|---|---|---|
| 4 | 9600 | 5.16 | 0.63 | 8.30 | 5.15 |
| 8 | 2400 | 0.15 | 0.18 | 0.40 | 5.91 |
| 16 | 600 | 0.13 | 0.11 | 0.24 | 6.78 |

  No attack: BER 0 everywhere.  Crop BER is about half the removed area for every b (lost blocks read as random bits).
* sigma_2 at delta = 4b is clearly worse (b=8: noise 4 -> 1.85 %, JPEG 75 -> 1.70 %; b=4: 9.0 % and 25.4 %).

## Theory vs experiment
* ||Aw - A||_F = ||Sw - S||_F: max relative difference 4.8e-14 over 150 images.
* Weyl: max over blocks of max_i |d sigma_i| / ||E||_2 = 0.9995 <= 1.
* sigma_1 drift under Gaussian noise has rms = noise std (0.998 / 2.00 / 4.00 / 8.03 for s = 1 / 2 / 4 / 8),
  so BER ~ 2 Q(delta / 2s).  Predicted vs measured BER (%), b = 8:
  delta 16, s 4: 4.55 vs 4.59;  delta 32, s 8: 4.55 vs 4.53;  delta 24, s 8: 13.36 vs 13.38;  delta 16, s 8: 31.73 vs 31.81.
* Rounding rule delta > b: no flips for delta >= b in any tested case; delta = b/4 at b = 4 flips 8.4 %.

## Statistical detectability (phase-concentration statistic on sigma / delta)
* Plain scheme: AUC 1.000 even when delta is unknown (sigma_1); the values pile up at the interval centres.
* With a secret key (per-block grid offset) AUC 0.36-0.44 (chance level for this statistic), with unchanged PSNR and BER
  (b=8, delta=32: 40.76 vs 40.77 dB).  Only this statistic was tested; stronger steganalysis is not claimed to fail.
* Wrong key -> message refused by the CRC check (tested).
