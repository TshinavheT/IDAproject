"""
Q8.1 uncertainty, calibration and fairness analysis of the locked model on the
held-out test year (2023 figures -> 2024 audit), plus the spread of the 2025 forecast.
Run from the project root (after src/forecast_next.py):  python src/fairness_q8.py

  Uncertainty  95% bootstrap confidence intervals (2,000 resamples, seed 42) for the
               test metrics; calibration (reliability) of the predicted probabilities.
  Fairness     test-year flag rate, recall (at-risk caught) and false-positive rate by
               province and by municipality type. Groups with fewer than 20
               municipalities, or fewer than 5 in a class, are marked as too small to judge.

Saves:
  results/q8_uncertainty.json
  results/q8_fairness_province.csv, results/q8_fairness_type.csv
  reports/figures/q8_fairness.png, reports/figures/q8_calibration.png
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (accuracy_score, brier_score_loss, f1_score, precision_score,
                             recall_score, roc_auc_score)

from evaluate_q4 import ACCENT
from models import SEED

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS = PROJECT_ROOT / "results"
FIGS = PROJECT_ROOT / "reports" / "figures"
N_BOOT = 2000
MIN_GROUP = 20
MIN_CLASS = 5

METRICS = {
    "accuracy": lambda y, p, s: accuracy_score(y, p),
    "macro_f1": lambda y, p, s: f1_score(y, p, average="macro"),
    "recall_at_risk": lambda y, p, s: recall_score(y, p),
    "precision_at_risk": lambda y, p, s: precision_score(y, p, zero_division=0),
    "roc_auc": lambda y, p, s: roc_auc_score(y, s),
}


def bootstrap(y, pred, prob):
    rng = np.random.RandomState(SEED)
    draws = {k: [] for k in METRICS}
    n = len(y)
    for _ in range(N_BOOT):
        idx = rng.randint(0, n, n)
        if len(np.unique(y[idx])) < 2:
            continue
        for k, f in METRICS.items():
            draws[k].append(f(y[idx], pred[idx], prob[idx]))
    out = {}
    for k, f in METRICS.items():
        lo, hi = np.percentile(draws[k], [2.5, 97.5])
        out[k] = {"estimate": float(f(y, pred, prob)), "ci95_low": float(lo), "ci95_high": float(hi)}
    return out


def group_table(df, column):
    rows = []
    for group, g in df.groupby(column):
        y, p = g["y"], g["p"]
        pos, neg = int(y.sum()), int((1 - y).sum())
        rows.append({
            column: group, "n": len(g), "actual_at_risk": pos, "actual_share": y.mean(),
            "flagged_share": p.mean(), "accuracy": (y == p).mean(),
            "recall_at_risk": (p[y == 1] == 1).mean() if pos else np.nan,
            "false_positive_rate": (p[y == 0] == 1).mean() if neg else np.nan,
            "reliable": len(g) >= MIN_GROUP and pos >= MIN_CLASS and neg >= MIN_CLASS,
        })
    return pd.DataFrame(rows).sort_values("n", ascending=False).reset_index(drop=True)


def main():
    scores = pd.read_csv(RESULTS / "municipality_scores.csv", low_memory=False)
    test = scores[scores["split"] == "test"].copy()
    test["y"] = (test["actual_next_outcome"] == "at_risk").astype(int)
    test["p"] = (test["predicted_outcome"] == "at_risk").astype(int)
    y, pred, prob = test["y"].to_numpy(), test["p"].to_numpy(), test["risk_probability"].to_numpy()

    # ---------- uncertainty ----------
    ci = bootstrap(y, pred, prob)
    frac_pos, mean_pred = calibration_curve(y, prob, n_bins=5, strategy="quantile")
    changed = test["prior_audit_outcome"] != test["actual_next_outcome"]
    fc = scores[scores["split"] == "forecast"]
    uncertainty = {
        "test_year": "2023 figures -> 2024 audit", "n_test": int(len(test)), "bootstrap_resamples": N_BOOT,
        "metrics_ci95": ci,
        "brier_score": float(brier_score_loss(y, prob)),
        "calibration_bins": [{"mean_predicted": float(m), "observed_at_risk": float(f)}
                             for m, f in zip(mean_pred, frac_pos)],
        "status_changes_in_test": int(changed.sum()),
        "accuracy_on_status_changes": float((test.loc[changed, "y"] == test.loc[changed, "p"]).mean()),
        "accuracy_on_stable": float((test.loc[~changed, "y"] == test.loc[~changed, "p"]).mean()),
        "forecast_2025": {
            "n": int(len(fc)), "flagged": int((fc["predicted_outcome"] == "at_risk").sum()),
            "close_calls_40_60": int(fc["risk_probability"].between(0.4, 0.6).sum()),
            "forecast_status_changes": int((fc["predicted_outcome"] != fc["prior_audit_outcome"]).sum()),
            "expected_status_changes_at_test_rate": float(changed.mean() * len(fc)),
        },
    }
    (RESULTS / "q8_uncertainty.json").write_text(json.dumps(uncertainty, indent=1))
    print("95% bootstrap CIs on the test year:")
    for k, v in ci.items():
        print(f"  {k:18s} {v['estimate']:.3f}  [{v['ci95_low']:.3f}, {v['ci95_high']:.3f}]")
    print(f"Brier score {uncertainty['brier_score']:.3f}; status changes in test year: {int(changed.sum())} "
          f"(accuracy on them {uncertainty['accuracy_on_status_changes']:.0%}, "
          f"on stable municipalities {uncertainty['accuracy_on_stable']:.0%})")

    # ---------- fairness ----------
    prov = group_table(test, "province")
    cat = group_table(test, "category")
    prov.to_csv(RESULTS / "q8_fairness_province.csv", index=False)
    cat.to_csv(RESULTS / "q8_fairness_type.csv", index=False)
    print("\nBy province:\n" + prov.round(3).to_string(index=False))
    print("\nBy municipality type:\n" + cat.round(3).to_string(index=False))

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), gridspec_kw={"width_ratios": [3, 1.3]})
    for ax, table, col, title in ((axes[0], prov.sort_values("province"), "province", "By province"),
                                  (axes[1], cat, "category", "By municipality type")):
        x = np.arange(len(table))
        w = 0.27
        ax.bar(x - w, table["recall_at_risk"], w, color=ACCENT, label="Recall (at-risk caught)")
        ax.bar(x, table["false_positive_rate"], w, color="#3B8DEB", label="False-positive rate")
        ax.bar(x + w, table["accuracy"], w, color="#22B07D", label="Accuracy")
        labels = [f"{g}\nn={n}{'' if ok else ' *'}" for g, n, ok in zip(table[col], table["n"], table["reliable"])]
        ax.set_xticks(x, labels, fontsize=8)
        ax.set(ylim=(0, 1.2), title=title, ylabel="Rate (0–1)")
        ax.axhline(ci["recall_at_risk"]["estimate"], color=ACCENT, ls=":", lw=1)
    axes[0].legend(loc="upper left", fontsize=8, ncol=3)
    fig.suptitle("Test-year (2024 audit) performance by group  ·  * = group too small to judge "
                 f"(n < {MIN_GROUP} or < {MIN_CLASS} per class)", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(FIGS / "q8_fairness.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5.5))
    ax.plot([0, 1], [0, 1], color="#C7CDD8", ls=":", label="Perfect calibration")
    ax.plot(mean_pred, frac_pos, "o-", color=ACCENT, lw=2, ms=8, label="Locked model (test year)")
    ax.set(xlim=(0, 1), ylim=(0, 1), title="Calibration — test year 2024 audit (5 equal-size bins)",
           xlabel="Mean predicted probability of a poor audit", ylabel="Observed share with a poor audit")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGS / "q8_calibration.png", dpi=150)
    plt.close(fig)
    print(f"\nSaved results/q8_*.csv/json and reports/figures/q8_fairness.png, q8_calibration.png")


if __name__ == "__main__":
    main()
