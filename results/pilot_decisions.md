# Pilot decisions (pilot set: 100 `val` images)

Scripts: `experiments/pilot_stego.py`, `experiments/pilot_watermark.py`.
Data: `results/pilot_stego.csv`, `results/pilot_watermark.csv`.

The pilot set (the 100 BSDS500 `val` images) shares **no image** with the evaluation set (the 400 `train` + `test`
images) from which every number in `findings.md` comes. Parameters are therefore never tuned on the images they
are judged on. (`results/image_sets.csv` lists which image is in which set.)

## Selection rule (written before looking at the results)
Keep configurations with mean PSNR >= 40 dB and < 0.5 % of blocks failing the closed-loop check;
among them prefer the lowest mean BER under Gaussian noise (std 4) plus JPEG (quality 75).

## Steganography
Grid: b in {4, 8, 16}, delta in {8, 12, 16, 24, 32, 48, 64}, sigma index k in {0, 1, 2, 3} (k = 0 is sigma_1).
All numbers use the closed-loop check with the safety margin (read-back sigma at least delta/4 from an interval edge,
`stego.embed_bits`); the margin was added after the demo showed clipped white blocks failing under JPEG 95.

* **Which singular value (k).**
  * k = 0 (sigma_1) fails the closed-loop check in 0 % of blocks in every configuration except one:
    b = 16 with delta = 8 (11 % failed). That is the case delta < b, where pixel rounding alone can move sigma
    across an interval boundary (rounding rule, `findings.md` → Theory).
  * k = 1 (sigma_2) fails in 0.03-0.44 % of blocks and is clearly less robust.
    Best passing k = 1 config at b = 8: delta = 24, BER 4.1 % (noise 4) and 3.7 % (JPEG 75),
    against 0.06 % and 0.08 % for the k = 0 winner.
  * k = 2 and 3 fail in 3-50 % of blocks (their sigma is tiny, so moving it by about one interval crosses a
    neighbouring sigma and the receiver's sorted order changes). Dropped.
* **PSNR depends on delta / b.** Configurations with the same delta / b have about the same PSNR
  (delta / b = 4 → 40.7-40.8 dB for b = 4, 8 and 16). At equal PSNR a larger block is more robust but carries fewer bits.
* **Winners** (the rule picks delta = 4b and k = 0 for every block size):

| b | bits per 480x320 image | delta | PSNR (dB) | images >= 40 dB | BER noise 4 | BER JPEG 75 |
|---|---|---|---|---|---|---|
| 4 | 9600 | 16 | 40.73 | 98 % | 5.11 % | 0.67 % |
| 8 | 2400 | 32 | 40.75 | 98 % | 0.06 % | 0.08 % |
| 16 | 600 | 64 | 40.76 | 98 % | 0.04 % | 0.02 % |

  The mean PSNR sits just above 40 dB, so about 2 % of individual images fall slightly below it.
  b = 8, delta = 32, k = 0 is used as the default in `stego.py` (2400 bits ≈ 296 bytes of text).
* **Caveat.** sigma_1 is about b times the block mean, so quantising it to a grid of delta quantises block brightness.
  PSNR does not see this, but a trained detector does: it shows up as small brightness steps at block borders
  (`ml_steganalysis.py`, findings.md → Trained detector).

## Watermarking (Liu-Tan)
* PSNR after rounding to 8 bit: 97.4 / 79.8 / 60.2 / 49.7 / 44.4 / 40.6 / 35.2 / 31.5 dB for
  alpha = 1 / 2 / 4 / 8 / 12 / 16 / 24 / 32. alpha = 16 is the last value with mean PSNR >= 40 dB.
* NCC of the extracted mark under noise 4 rises from 0.58 (alpha 1) to 0.98 (alpha 8) and >= 0.99 for alpha >= 12.
* **NCC is not proof.** Extracting with the key from the ORIGINAL image (never watermarked) also gives NCC
  0.98 / 0.97 / 0.96 at alpha 8 / 12 / 16, because the key (Uw, Vw) carries most of the mark.
  From a DIFFERENT image NCC is only 0.02-0.46. A second, key-independent test is needed → `shift_score` in `watermark.py`.

## Grid for the full run (evaluation set)
* Steganography: k = 0 (main) and k = 1 (comparison); b in {4, 8, 16}; delta = c * b with c in {2, 3, 4, 6, 8}.
* Watermarking: alpha in {2, 4, 8, 12, 16, 24} (24 shown as the point beyond the 40 dB target).
* Attacks as in `attacks.LEVELS` (fixed before any result was seen).
