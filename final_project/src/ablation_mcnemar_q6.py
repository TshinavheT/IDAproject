"""
Q6 controlled ablations and McNemar's test.
Run from the project root:  python src/ablation_mcnemar_q6.py

Q6.1  Ablations on the tuned champion (Logistic Regression, Q5 hyperparameters).
      Exactly one thing changes per experiment; split (fit 2018-2021), seed (42)
      and evaluation protocol (validation 2022 + walk-forward CV 2019-2021) are fixed.
      The 2023 test year is not used here: it was spent once in Q5.3.

Q6.2  McNemar's test: tuned champion vs the strongest comparator (MLP, best
      non-champion on validation macro-F1, tie broken by ROC-AUC). Both are fit on
      2018-2022 and predict the SAME 2023 municipalities. Exact binomial version is
      used when discordant counts are small (b + c < 25).

Saves:
  results/q6_ablation.csv, reports/figures/q6_ablation.png
  results/q6_mcnemar.json, reports/figures/q6_mcnemar_table.png
  results/q6_paired_test_predictions.csv
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.stats.contingency_tables import mcnemar

from evaluate_q4 import ACCENT, COLORS, score, walk_forward_cv
from models import SEED, build_models
from pipeline_q24 import CATEGORICAL_FEATURES, NUMERIC_FEATURES, TARGET_COL, TARGET_MAP

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA = PROJECT_ROOT / "data" / "processed"
RESULTS = PROJECT_ROOT / "results"
FIGS = PROJECT_ROOT / "reports" / "figures"

COMPARATOR = "MLP"
ALPHA = 0.05


def champion_pipeline(numeric=NUMERIC_FEATURES, categorical=CATEGORICAL_FEATURES,
                      scale=True, class_weight="balanced", l1_ratio=1.0, C=None):
    """Tuned champion from Q5, with switches for the one-at-a-time ablations."""
    best = json.loads((RESULTS / "q5_test_result.json").read_text())["best_params"]
    num_steps = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        num_steps.append(("scale", StandardScaler()))
    transformers = []
    if numeric:
        transformers.append(("num", Pipeline(num_steps), list(numeric)))
    if categorical:
        transformers.append(("cat", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore"))]), list(categorical)))
    clf = LogisticRegression(C=C or best["C"], l1_ratio=l1_ratio,
                             solver="saga" if l1_ratio > 0 else "lbfgs",
                             class_weight=class_weight, max_iter=5000, random_state=SEED)
    return Pipeline([("preprocess", ColumnTransformer(transformers)), ("model", clf)])


ABLATIONS = {
    "Full tuned champion (reference)": {},
    "A1: remove audit-history feature (prior_audit_outcome)": {"categorical": []},
    "A2: remove financial-ratio feature group (9 ratios)": {"numeric": []},
    "A3: remove imbalance treatment (no class weighting)": {"class_weight": None},
    "A4: remove scaling step (raw rand-scale values)": {"scale": False},
    "A5: swap L1 regulariser for L2": {"l1_ratio": 0.0},
}


def run_ablations(train_df, val_df):
    y_train, y_val = train_df[TARGET_COL].map(TARGET_MAP), val_df[TARGET_COL].map(TARGET_MAP)
    rows = []
    for name, change in ABLATIONS.items():
        pipe = champion_pipeline(**change)
        cv = walk_forward_cv(pipe, train_df)
        fitted = clone(pipe).fit(train_df, y_train)
        va = score(y_val, fitted.predict(val_df), fitted.predict_proba(val_df)[:, 1])
        rows.append({"experiment": name, "cv_macro_f1_mean": cv["macro_f1"].mean(),
                     "cv_macro_f1_std": cv["macro_f1"].std(ddof=1),
                     **{f"val_{k}": v for k, v in va.items()}})
        print(f"{name:58s} val macro-F1={va['macro_f1']:.4f}  ROC-AUC={va['roc_auc']:.4f}  "
              f"recall(at_risk)={va['recall_at_risk']:.4f}  CV={cv['macro_f1'].mean():.4f}")
    df = pd.DataFrame(rows)
    ref = df.iloc[0]
    for col in ["val_macro_f1", "val_roc_auc", "val_recall_at_risk", "cv_macro_f1_mean"]:
        df[f"delta_{col}"] = df[col] - ref[col]
    return df


def plot_ablations(df):
    abl = df.iloc[1:]
    labels = [e.split(": ", 1)[1] for e in abl["experiment"]]
    y = np.arange(len(abl))
    fig, ax = plt.subplots(figsize=(10, 5))
    h = 0.38
    b1 = ax.barh(y - h / 2, abl["delta_val_macro_f1"], h, color=ACCENT, label="Δ validation macro-F1")
    b2 = ax.barh(y + h / 2, abl["delta_val_roc_auc"], h, color="#3B8DEB", label="Δ validation ROC-AUC")
    ax.bar_label(b1, fmt="%+.3f", fontsize=8, padding=3)
    ax.bar_label(b2, fmt="%+.3f", fontsize=8, padding=3)
    ax.axvline(0, color="#2E3546", lw=1)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    lo = min(abl["delta_val_macro_f1"].min(), abl["delta_val_roc_auc"].min())
    ax.set_xlim(lo - 0.08, 0.08)
    ax.set(title="Ablation study — change vs the full tuned champion\n(fit 2018–2021, validation year 2022)",
           xlabel="Change in score (negative = the model depends on this component)")
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(FIGS / "q6_ablation.png", dpi=150)
    plt.close(fig)


def run_mcnemar(train_df, val_df):
    final_df = pd.concat([train_df, val_df], ignore_index=True)
    y_final = final_df[TARGET_COL].map(TARGET_MAP)
    test_df = pd.read_csv(DATA / "test.csv", low_memory=False)
    y_test = test_df[TARGET_COL].map(TARGET_MAP).to_numpy()

    champ = pd.read_csv(RESULTS / "q5_test_predictions.csv")
    assert (champ["demarcation.code"].to_numpy() == test_df["demarcation.code"].to_numpy()).all()
    champ_pred = champ["champion_pred"].to_numpy()

    comparator = clone(build_models()[COMPARATOR]).fit(final_df, y_final)
    comp_pred = comparator.predict(test_df)
    comp_prob = comparator.predict_proba(test_df)[:, 1]

    champ_ok, comp_ok = champ_pred == y_test, comp_pred == y_test
    a = int(np.sum(champ_ok & comp_ok))      # both correct
    b = int(np.sum(champ_ok & ~comp_ok))     # champion only correct
    c = int(np.sum(~champ_ok & comp_ok))     # comparator only correct
    d = int(np.sum(~champ_ok & ~comp_ok))    # both wrong
    table = np.array([[a, b], [c, d]])

    exact = b + c < 25
    res = mcnemar(table, exact=exact, correction=True)
    p_value = float(res.pvalue)
    result = {
        "champion": "Logistic Regression (tuned, Q5)", "comparator": f"{COMPARATOR} (Q3 configuration)",
        "fit_years": "2018-2022", "test_year": 2023, "n_test": int(len(y_test)),
        "table": {"both_correct": a, "champion_only_correct": b,
                  "comparator_only_correct": c, "both_wrong": d},
        "discordant_pairs": b + c,
        "H0": "The two models have the same error rate on these municipalities (P(b) = P(c)).",
        "H1": "The two models have different error rates (P(b) != P(c)), two-sided.",
        "alpha": ALPHA,
        "test_version": "exact binomial (b + c < 25)" if exact else "chi-square with continuity correction",
        "statistic": float(res.statistic),
        "p_value": p_value,
        "reject_H0": p_value < ALPHA,
        "champion_macro_f1": float(f1_score(y_test, champ_pred, average="macro")),
        "comparator_macro_f1": float(f1_score(y_test, comp_pred, average="macro")),
        "champion_accuracy": float(champ_ok.mean()),
        "comparator_accuracy": float(comp_ok.mean()),
    }
    if b + c > 0:
        result["exact_binomial_p_value"] = float(binomtest(min(b, c), b + c, 0.5).pvalue)

    pd.DataFrame({"demarcation.code": test_df["demarcation.code"], "Name": test_df["Name"],
                  "y_true": y_test, "champion_pred": champ_pred, "comparator_pred": comp_pred,
                  "comparator_prob": comp_prob, "champion_correct": champ_ok.astype(int),
                  "comparator_correct": comp_ok.astype(int)}).to_csv(
        RESULTS / "q6_paired_test_predictions.csv", index=False)

    fig, ax = plt.subplots(figsize=(6.4, 5))
    ax.imshow(np.array([[1, 0], [0, 1]]), cmap="Blues", alpha=0.15)
    cells = [["Both correct", "Champion only\ncorrect"], ["Comparator only\ncorrect", "Both wrong"]]
    for i in range(2):
        for j in range(2):
            ax.text(j, i - 0.08, str(table[i, j]), ha="center", va="center", fontsize=26,
                    fontweight="bold", color=ACCENT if i != j else "#2E3546")
            ax.text(j, i + 0.22, cells[i][j], ha="center", va="center", fontsize=9, color="#5B6475")
    ax.set_xticks([0, 1], ["MLP correct", "MLP wrong"])
    ax.set_yticks([0, 1], ["Champion correct", "Champion wrong"])
    ax.grid(False)
    ax.set_title(f"McNemar 2×2 — tuned LR vs MLP, test year 2023 (n = {len(y_test)})\n"
                 f"{result['test_version']}: p = {p_value:.4f} (α = {ALPHA})", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIGS / "q6_mcnemar_table.png", dpi=150)
    plt.close(fig)
    return result


def main():
    RESULTS.mkdir(exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    train_df = pd.read_csv(DATA / "train.csv", low_memory=False)
    val_df = pd.read_csv(DATA / "val.csv", low_memory=False)

    print("=== Q6.1 Ablations (fit 2018-2021, evaluate 2022 + walk-forward CV) ===")
    abl = run_ablations(train_df, val_df)
    abl.to_csv(RESULTS / "q6_ablation.csv", index=False)
    plot_ablations(abl)

    print("\n=== Q6.2 McNemar (fit 2018-2022, same 2023 municipalities) ===")
    result = run_mcnemar(train_df, val_df)
    (RESULTS / "q6_mcnemar.json").write_text(json.dumps(result, indent=1))
    t = result["table"]
    print(f"Both correct={t['both_correct']}  Champion only={t['champion_only_correct']}  "
          f"Comparator only={t['comparator_only_correct']}  Both wrong={t['both_wrong']}")
    print(f"{result['test_version']}: statistic={result['statistic']:.4f}  p={result['p_value']:.4f}  "
          f"reject H0 at {ALPHA}: {result['reject_H0']}")
    print(f"Champion acc={result['champion_accuracy']:.4f} macro-F1={result['champion_macro_f1']:.4f} | "
          f"MLP acc={result['comparator_accuracy']:.4f} macro-F1={result['comparator_macro_f1']:.4f}")


if __name__ == "__main__":
    main()
