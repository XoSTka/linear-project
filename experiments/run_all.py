"""Run the whole pipeline in order (about 1 hour on a 2-core machine).

    python experiments/run_all.py            # everything
    python experiments/run_all.py full_stego # only the named steps (any subset, kept in pipeline order)

Each step's console output is also written to logs/<step>.log.
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    "prepare_data",  # image sets + singular values of the evaluation images
    "pilot_stego",  # choose b, delta, k        (pilot set: 100 val images)
    "pilot_watermark",  # choose alpha              (pilot set)
    "full_stego",  # every reported stego number       (eval set: 400 train+test images)
    "full_watermark",  # every reported watermark number   (eval set)
    "analyze_stego",  # summaries of full_stego.csv
    "analyze_watermark",  # summaries + detection AUC of full_watermark.csv
    "steganalysis",  # can a simple statistic detect the stego images?
    "ml_steganalysis",  # can a trained detector (machine learning) detect them?
    "robustness_extra",  # does a whole message survive? error correction on/off, extra attacks
    "key_strength",  # how long does guessing the secret key take? (old vs new key derivation)
    "theory_checks",  # theory vs measurement
    "make_report_assets",  # figures and tables for the report and slides
]

if __name__ == "__main__":
    wanted = sys.argv[1:] or STEPS
    unknown = set(wanted) - set(STEPS)
    if unknown:
        sys.exit(f"unknown step(s): {', '.join(sorted(unknown))}; choose from {', '.join(STEPS)}")
    (ROOT / "logs").mkdir(exist_ok=True)
    t_all = time.time()
    for step in [s for s in STEPS if s in wanted]:
        t0 = time.time()
        print(f"=== {step}", flush=True)
        with open(ROOT / "logs" / f"{step}.log", "w", encoding="utf-8") as log:
            proc = subprocess.Popen(
                [sys.executable, str(ROOT / "experiments" / f"{step}.py")],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
            )
            for line in proc.stdout:
                print(line, end="", flush=True)
                log.write(line)
            if proc.wait() != 0:
                sys.exit(f"step {step} failed (exit code {proc.returncode}); see logs/{step}.log")
        print(f"=== {step} done in {time.time() - t0:.0f}s", flush=True)
    print(f"all done in {(time.time() - t_all) / 60:.1f} min")
