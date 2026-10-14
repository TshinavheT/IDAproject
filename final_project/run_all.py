"""
Reproduce every result, figure, saved model and report section in the documented order.
Run from anywhere:  python run_all.py            (uses the cached data in data/raw)
                    python run_all.py --download (first re-downloads data/raw from the API)

Each step is a separate script in src/; the run stops at the first failure.
All randomness is seeded with 42 (src/models.py: SEED).
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STEPS = [
    ("Q2.1 data audit", "src/audit_q21_v2.py"),
    ("Q2.2 visualisations", "src/visualize_q22_v2.py"),
    ("Q2.3 time-based split", "src/split_q23_v2.py"),
    ("Q2.4 preprocessing pipeline", "src/pipeline_q24.py"),
    ("Q3 baseline and models", "src/train_q3.py"),
    ("Q4 evaluation and overfitting", "src/evaluate_q4.py"),
    ("Q5 optimisation and one-time test", "src/optimise_q5.py"),
    ("Q6 ablations and McNemar", "src/ablation_mcnemar_q6.py"),
    ("Q7 scores and 2025 forecast", "src/forecast_next.py"),
    ("Q8 uncertainty and fairness", "src/fairness_q8.py"),
    ("Experiment log", "src/experiment_log.py"),
]


def main():
    steps = list(STEPS)
    if "--download" in sys.argv:
        steps.insert(0, ("Q2 download and build dataset", "src/build_modeling_dataset.py"))
    start = time.time()
    for i, (name, script) in enumerate(steps, 1):
        print(f"\n[{i}/{len(steps)}] {name}  ({script})", flush=True)
        t = time.time()
        result = subprocess.run([sys.executable, "-W", "ignore", str(ROOT / script)], cwd=ROOT)
        if result.returncode != 0:
            sys.exit(f"Step failed: {script}")
        print(f"      done in {time.time() - t:.0f}s", flush=True)
    print(f"\nAll {len(steps)} steps finished in {(time.time() - start) / 60:.1f} min.")
    print("Launch the dashboard with:  streamlit run app/app.py")


if __name__ == "__main__":
    main()
