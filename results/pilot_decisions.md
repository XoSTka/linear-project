# Pilot decisions (validation split, 30 images)

Scripts: `experiments/pilot_stego.py`, `experiments/pilot_watermark.py`.
Data: `results/pilot_stego.csv`, `results/pilot_watermark.csv`.
The pilot used only the 30 `val` images of the 150-image sample, so the full run can report on all 150 without having tuned on them.

## Selection rule (written before looking at the results)
Keep configurations with mean PSNR >= 40 dB and < 0.5 % of blocks failing the closed-loop check;
among them prefer the lowest mean BER under Gaussian noise (std 4) and JPEG (quality 75).

## Steganography
* **Which singular value (k).** k=0 (sigma_1) never failed the closed-loop check and was the most robust.
  k=2 and k=3 failed in 5-47 % of blocks (their sigma is tiny, so moving it by about one interval crosses a neighbour).
  k=1 works but is clearly less robust (b=8, best config: BER 4.7 % vs 0.10 % for k=0).
* **PSNR depends on delta / b.** Configs with the same delta/b have about the same PSNR (delta/b = 4 -> ~40.7 dB for b = 4, 8, 16).
  At equal PSNR a larger block is more robust but carries fewer bits:

| b | bits per 480x320 image | best delta (k=0) | PSNR | BER noise4 | BER jpeg75 |
|---|---|---|---|---|---|
| 4 | 9600 | 16 | 40.7 | 5.15 % | 0.72 % |
| 8 | 2400 | 32 | 40.7 | 0.11 % | 0.10 % |
| 16 | 600 | 64 | 40.8 | 0.12 % | 0.07 % |

* **Caveat.** sigma_1 is about b times the block mean, so rounding it to a grid of delta quantises the block brightness.
  PSNR does not see this; a statistical test might (task #19).

## Watermarking (Liu-Tan)
* alpha = 16 is the last value meeting PSNR >= 40 dB (40.6 dB after rounding to 8 bit); alpha = 8 gives 49.7 dB.
* Under attack NCC stays >= 0.98 for alpha >= 8, but extraction from the ORIGINAL image (never watermarked)
  also gives NCC 0.96-0.98 at alpha 8-16. The mark comes from the key, not from the image, so NCC alone is not proof (task #14).
* PSNR in the CSV is capped at 99 dB where the 8-bit image equals the original (alpha = 1).

## Grid for the full run (task #8)
* Steganography: k = 0 (main) and k = 1 (comparison); b in {4, 8, 16}; delta = c * b with c in {2, 3, 4, 6, 8}.
* Watermarking: alpha in {2, 4, 8, 12, 16, 24} (24 shown as the beyond-target point).
* Attacks as in `attacks.LEVELS`.
