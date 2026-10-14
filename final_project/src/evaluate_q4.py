"""
Q4 evaluation, comparison and overfitting diagnosis.
Run from the project root:  python src/evaluate_q4.py

All models are fit on the training years (2018-2021) and compared on the same
validation year (2022). The 2023 test year is still not loaded.

  Q4.1  results/q4_validation_metrics.csv     same metric set for every model
  Q4.2  results/q4_classification_reports.txt per-model reports with support
        reports/figures/q4_confusion_matrices.png
        reports/figures/q4_roc_curves.png      all models on one figure
        reports/figures/q4_pr_curves.png       PR-AUC is reported for the minority class
  Q4.3  results/q4_cv_walk_forward.csv        walk-forward CV mean/std inside training years
        reports/figures/q4_model_comparison.png
  Q4.4  results/q4_overfitting_gap.csv
        reports/figures/q4_learning_curves.png
        reports/figures/q4_neural_training_curves.png
  results/dashboard_q4.json                   numbers the Streamlit dashboard reads
"""

import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score,
                             average_precision_score, classification_report,
                             confusion_matrix, f1_score, precision_recall_curve,
                             precision_score, recall_score, roc_auc_score, roc_curve)

from models import BASELINES, SEED, build_models
from pipeline_q24 import TARGET_COL, TARGET_MAP, load_split

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS = PROJECT_ROOT / "results"
FIGS = PROJECT_ROOT / "reports" / "figures"
TRAIN_CSV = PROJECT_ROOT / "data" / "processed" / "train.csv"

LABELS = ["not_at_risk", "at_risk"]
COLORS = {
    "Baseline (Dummy)": "#A0A8B8",
    "Baseline (Repeat last year)": "#5B6475",
    "Logistic Regression": "#3B8DEB",
    "Random Forest": "#22B07D",
    "MLP": "#F5A524",
    "Residual Tabular NN": "#8B5CF6",
}
ACCENT = "#F0507A"

plt.rcParams.update({
    "figure.facecolor": "#F4F6FA", "axes.facecolor": "#FFFFFF",
    "axes.edgecolor": "#D9DEE7", "axes.grid": True, "grid.color": "#ECEFF4",
    "axes.titleweight": "bold", "axes.titlesize": 12, "font.size": 10,
    "axes.labelcolor": "#2E3546", "xtick.color": "#5B6475", "ytick.color": "#5B6475",
})


def score(y_true, y_pred, y_prob):
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "precision_at_risk": precision_score(y_true, y_pred, zero_division=0),
        "recall_at_risk": recall_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_prob),
        "pr_auc": average_precision_score(y_true, y_prob),
    }


def walk_forward_cv(model, train_df):
    """Expanding-window CV inside the training years: 2018->2019, 2018-19->2020, 2018-20->2021."""
    years = sorted(train_df["financial_year_end.year"].unique())
    X_all, y_all = train_df, train_df[TARGET_COL].map(TARGET_MAP)
    scores = []
    for i in range(1, len(years)):
        tr = train_df["financial_year_end.year"].isin(years[:i])
        va = train_df["financial_year_end.year"] == years[i]
        m = clone(model).fit(X_all[tr], y_all[tr])
        scores.append({"fold_val_year": years[i],
                       "macro_f1": f1_score(y_all[va], m.predict(X_all[va]), average="macro"),
                       "accuracy": accuracy_score(y_all[va], m.predict(X_all[va]))})
    return pd.DataFrame(scores)


def learning_curve(model, X, y, X_val, y_val, fractions=(0.2, 0.4, 0.6, 0.8, 1.0)):
    rng = np.random.RandomState(SEED)
    rows = []
    for frac in fractions:
        idx = []
        for cls in (0, 1):  # stratified subsample of the training years
            cls_idx = np.where(y.values == cls)[0]
            idx.extend(rng.choice(cls_idx, int(round(frac * len(cls_idx))), replace=False))
        idx = np.sort(idx)
        m = clone(model).fit(X.iloc[idx], y.iloc[idx])
        rows.append({"n_train": len(idx),
                     "train_macro_f1": f1_score(y.iloc[idx], m.predict(X.iloc[idx]), average="macro"),
                     "val_macro_f1": f1_score(y_val, m.predict(X_val), average="macro")})
    return pd.DataFrame(rows)


def main():
    RESULTS.mkdir(exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)

    X_train, y_train = load_split("train")
    X_val, y_val = load_split("val")
    train_df = pd.read_csv(TRAIN_CSV, low_memory=False)

    models = build_models()
    fitted, rows, probs, preds, reports = {}, [], {}, {}, []

    # ---------- Q4.1 + Q4.2: same metrics, reports and confusion matrices for every model ----------
    for name, model in models.items():
        m = clone(model).fit(X_train, y_train)
        fitted[name] = m
        probs[name] = m.predict_proba(X_val)[:, 1]
        preds[name] = m.predict(X_val)
        tr_pred, tr_prob = m.predict(X_train), m.predict_proba(X_train)[:, 1]

        va, tr = score(y_val, preds[name], probs[name]), score(y_train, tr_pred, tr_prob)
        rows.append({"model": name, "type": "baseline" if name in BASELINES else "substantive",
                     **{f"val_{k}": v for k, v in va.items()},
                     **{f"train_{k}": v for k, v in tr.items()}})
        reports.append(f"===== {name} (validation year 2022, n={len(y_val)}) =====\n"
                       + classification_report(y_val, preds[name], target_names=LABELS, digits=3))
        print(f"{name:28s} val macro-F1={va['macro_f1']:.4f}  ROC-AUC={va['roc_auc']:.4f}  "
              f"PR-AUC={va['pr_auc']:.4f}")

    metrics = pd.DataFrame(rows)
    metrics.to_csv(RESULTS / "q4_validation_metrics.csv", index=False)
    (RESULTS / "q4_classification_reports.txt").write_text("\n".join(reports))
    pd.DataFrame({"y_true": y_val.values,
                  **{f"{n}__pred": p for n, p in preds.items()},
                  **{f"{n}__prob": p for n, p in probs.items()}}).to_csv(
        RESULTS / "q4_val_predictions.csv", index=False)

    fig, axes = plt.subplots(2, 3, figsize=(14, 8.5))
    for ax, name in zip(axes.ravel(), models):
        cm = confusion_matrix(y_val, preds[name], labels=[0, 1])
        ConfusionMatrixDisplay(cm, display_labels=LABELS).plot(
            ax=ax, cmap="Blues", colorbar=False, values_format="d")
        ax.set_title(name, color=COLORS[name])
        ax.set_xlabel("Predicted class (year t+1)")
        ax.set_ylabel("Actual class (year t+1)")
        ax.grid(False)
    fig.suptitle("Confusion matrices — validation year 2022 (n = 244 municipalities)",
                 fontweight="bold", fontsize=14)
    fig.tight_layout()
    fig.savefig(FIGS / "q4_confusion_matrices.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    for name in models:
        fpr, tpr, _ = roc_curve(y_val, probs[name])
        ax.plot(fpr, tpr, lw=2.2, color=COLORS[name],
                ls="--" if name in BASELINES else "-",
                label=f"{name} (AUC = {roc_auc_score(y_val, probs[name]):.3f})")
    ax.plot([0, 1], [0, 1], color="#C7CDD8", lw=1, ls=":")
    ax.set(title="ROC curves — validation year 2022 (positive class: at_risk)",
           xlabel="False positive rate (share of healthy municipalities flagged)",
           ylabel="True positive rate (share of at-risk municipalities caught)")
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGS / "q4_roc_curves.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    for name in models:
        p, r, _ = precision_recall_curve(y_val, probs[name])
        ax.plot(r, p, lw=2.2, color=COLORS[name], ls="--" if name in BASELINES else "-",
                label=f"{name} (AP = {average_precision_score(y_val, probs[name]):.3f})")
    ax.axhline(y_val.mean(), color="#C7CDD8", lw=1, ls=":", label=f"Prevalence = {y_val.mean():.2f}")
    ax.set(title="Precision–recall curves — validation year 2022 (positive class: at_risk)",
           xlabel="Recall (at_risk)", ylabel="Precision (at_risk)")
    ax.legend(loc="lower left", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGS / "q4_pr_curves.png", dpi=150)
    plt.close(fig)

    # ---------- Q4.3: walk-forward CV variability + comparison chart ----------
    cv_rows = []
    for name, model in models.items():
        cv = walk_forward_cv(model, train_df)
        cv_rows.append({"model": name, "cv_macro_f1_mean": cv["macro_f1"].mean(),
                        "cv_macro_f1_std": cv["macro_f1"].std(ddof=1),
                        "cv_accuracy_mean": cv["accuracy"].mean(),
                        "cv_accuracy_std": cv["accuracy"].std(ddof=1),
                        **{f"fold_{int(r.fold_val_year)}_macro_f1": r.macro_f1 for r in cv.itertuples()}})
    cv_df = pd.DataFrame(cv_rows)
    cv_df.to_csv(RESULTS / "q4_cv_walk_forward.csv", index=False)
    comparison = metrics.merge(cv_df, on="model")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    names = list(models)
    x = np.arange(len(names))
    w = 0.26
    for i, (col, label, color) in enumerate([("val_accuracy", "Accuracy", "#3B8DEB"),
                                              ("val_macro_f1", "Macro-F1", ACCENT),
                                              ("val_roc_auc", "ROC-AUC", "#22B07D")]):
        vals = comparison.set_index("model").loc[names, col]
        bars = axes[0].bar(x + (i - 1) * w, vals, w, label=label, color=color)
        axes[0].bar_label(bars, fmt="%.2f", fontsize=7, padding=2)
    axes[0].set_xticks(x, [textwrap.fill(n, 14) for n in names], fontsize=8)
    axes[0].set(ylim=(0, 1.08), ylabel="Score (0–1)", title="Validation-year (2022) scores")
    axes[0].legend(loc="lower right")

    cvp = comparison.set_index("model").loc[names]
    axes[1].bar(x, cvp["cv_macro_f1_mean"], yerr=cvp["cv_macro_f1_std"], capsize=6,
                color=[COLORS[n] for n in names])
    for xi, (m, s) in enumerate(zip(cvp["cv_macro_f1_mean"], cvp["cv_macro_f1_std"])):
        axes[1].text(xi, m + s + 0.02, f"{m:.3f}\n±{s:.3f}", ha="center", fontsize=8)
    axes[1].set_xticks(x, [textwrap.fill(n, 14) for n in names], fontsize=8)
    axes[1].set(ylim=(0, 1.1), ylabel="Macro-F1 (mean ± SD, 3 folds)",
                title="Walk-forward CV within training years (2019–2021 folds)")
    fig.suptitle("Model comparison", fontweight="bold", fontsize=14)
    fig.tight_layout()
    fig.savefig(FIGS / "q4_model_comparison.png", dpi=150)
    plt.close(fig)

    substantive = comparison[comparison["type"] == "substantive"]
    champion = substantive.sort_values(["val_macro_f1", "val_roc_auc"], ascending=False).iloc[0]["model"]
    print(f"\nProvisional champion on validation macro-F1 (ties broken by ROC-AUC): {champion}")

    # ---------- Q4.4: overfitting — gaps, learning curves, neural curves ----------
    gap = metrics[["model", "train_macro_f1", "val_macro_f1", "train_accuracy", "val_accuracy"]].copy()
    gap["macro_f1_gap"] = gap["train_macro_f1"] - gap["val_macro_f1"]
    gap["accuracy_gap"] = gap["train_accuracy"] - gap["val_accuracy"]
    gap.to_csv(RESULTS / "q4_overfitting_gap.csv", index=False)
    print("\nTrain - validation macro-F1 gap:")
    print(gap[["model", "train_macro_f1", "val_macro_f1", "macro_f1_gap"]].round(4).to_string(index=False))

    sub_names = substantive["model"].tolist()
    curves = {}
    fig, axes = plt.subplots(1, len(sub_names), figsize=(4.2 * len(sub_names), 4.2), sharey=True)
    for ax, name in zip(axes, sub_names):
        lc = learning_curve(models[name], X_train, y_train, X_val, y_val)
        curves[name] = lc
        ax.plot(lc["n_train"], lc["train_macro_f1"], "o-", color=COLORS[name], lw=2, label="Training")
        ax.plot(lc["n_train"], lc["val_macro_f1"], "s--", color=ACCENT, lw=2, label="Validation 2022")
        ax.fill_between(lc["n_train"], lc["val_macro_f1"], lc["train_macro_f1"], color=COLORS[name], alpha=0.1)
        ax.set(title=name, xlabel="Training rows (municipality-years)", ylim=(0.6, 1.02))
        ax.legend(loc="lower right", fontsize=8)
    axes[0].set_ylabel("Macro-F1")
    fig.suptitle("Learning curves — training vs validation macro-F1", fontweight="bold", fontsize=14)
    fig.tight_layout()
    fig.savefig(FIGS / "q4_learning_curves.png", dpi=150)
    plt.close(fig)

    neural = [n for n in sub_names if hasattr(fitted[n], "named_steps")
              and hasattr(fitted[n].named_steps["model"], "history_")]
    fig, axes = plt.subplots(len(neural), 2, figsize=(12, 4.2 * len(neural)))
    nn_info = {}
    for row, name in zip(np.atleast_2d(axes), neural):
        clf = fitted[name].named_steps["model"]
        h = clf.history_
        ep = np.arange(1, len(h["train_loss"]) + 1)
        row[0].plot(ep, h["train_loss"], color=COLORS[name], lw=2, label="Training loss")
        row[0].plot(ep, h["es_loss"], color=ACCENT, lw=2, ls="--", label="Early-stopping loss")
        row[1].plot(ep, h["train_acc"], color=COLORS[name], lw=2, label="Training accuracy")
        row[1].plot(ep, h["es_acc"], color=ACCENT, lw=2, ls="--", label="Early-stopping accuracy")
        for ax in row:
            ax.axvline(clf.best_epoch_, color="#5B6475", ls=":", lw=1.2,
                       label=f"Best epoch = {clf.best_epoch_}")
            ax.set_xlabel("Epoch")
            ax.legend(fontsize=8)
        row[0].set(title=f"{name} — weighted cross-entropy loss", ylabel="Loss")
        row[1].set(title=f"{name} — accuracy", ylabel="Accuracy (0–1)")
        nn_info[name] = {"best_epoch": clf.best_epoch_, "epochs_run": clf.n_epochs_run_,
                         **{k: [round(v, 4) for v in vals] for k, vals in h.items()}}
    fig.suptitle("Neural networks — training vs early-stopping curves "
                 "(early-stopping set = 15% of training years)", fontweight="bold", fontsize=13)
    fig.tight_layout()
    fig.savefig(FIGS / "q4_neural_training_curves.png", dpi=150)
    plt.close(fig)

    # ---------- Numbers for the dashboard ----------
    dashboard = {
        "champion": champion,
        "n_train": int(len(y_train)), "n_val": int(len(y_val)),
        "val_at_risk_share": float(y_val.mean()),
        "models": comparison.round(4).to_dict(orient="records"),
        "confusion": {n: confusion_matrix(y_val, preds[n], labels=[0, 1]).tolist() for n in models},
        "roc": {n: {k: v.round(4).tolist() for k, v in zip(("fpr", "tpr"), roc_curve(y_val, probs[n])[:2])}
                for n in models},
        "learning_curves": {n: lc.round(4).to_dict(orient="list") for n, lc in curves.items()},
        "neural_history": nn_info,
    }
    (RESULTS / "dashboard_q4.json").write_text(json.dumps(dashboard, indent=1))
    print(f"\nSaved figures to {FIGS} and tables to {RESULTS}")


if __name__ == "__main__":
    main()
