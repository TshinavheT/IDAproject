"""
Q5 champion optimisation and the one-time test evaluation.
Run from the project root:  python src/optimise_q5.py

Champion from Q4 (validation macro-F1): Logistic Regression.

  Q5.1  Optuna TPE search (seeded), 60 trials. Search space below.
        Scoring rule: mean macro-F1 over walk-forward folds inside the training
        years (train 2018 -> score 2019, 2018-19 -> 2020, 2018-20 -> 2021).
  Q5.2  The validation year (2022) and test year (2023) are never used for scoring.
        Pre/post comparison is reported on the CV folds and on validation 2022.
  Q5.3  The tuned pipeline is locked, refit on 2018-2022 and scored ONCE on 2023.

Saves:
  models/final_pipeline.joblib            locked pipeline used by the app
  results/q5_optuna_trials.csv            every trial and its score
  results/q5_pre_post.csv                 default vs tuned comparison
  results/q5_test_result.json             the one-time test evaluation
  results/q5_test_predictions.csv         2023 predictions (used by McNemar in Q6)
  reports/figures/q5_optimisation_history.png
  reports/figures/q5_test_confusion_matrix.png
"""

import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import optuna
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, classification_report,
                             confusion_matrix, f1_score)
from sklearn.preprocessing import RobustScaler, StandardScaler

from evaluate_q4 import ACCENT, score, walk_forward_cv
from models import SEED, PriorOutcomeRule, build_models
from pipeline_q24 import TARGET_COL, TARGET_MAP

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA = PROJECT_ROOT / "data" / "processed"
RESULTS = PROJECT_ROOT / "results"
FIGS = PROJECT_ROOT / "reports" / "figures"
MODELS = PROJECT_ROOT / "models"

CHAMPION = "Logistic Regression"
N_TRIALS = 60
LABELS = ["not_at_risk", "at_risk"]

SEARCH_SPACE = {
    "C": "log-uniform 0.001 - 100 (inverse regularisation strength)",
    "penalty": "l2 | l1 | elasticnet",
    "l1_ratio": "0.05 - 0.95 (elasticnet only)",
    "class_weight": "balanced | none",
    "scaler": "standard | robust (robust is less sensitive to the large outliers found in Q2.1)",
}


def configure(params):
    """Build the champion pipeline from one set of hyperparameters."""
    pipe = clone(build_models()[CHAMPION])
    penalty = params["penalty"]
    clf = LogisticRegression(
        C=params["C"],
        l1_ratio={"l2": 0.0, "l1": 1.0}.get(penalty, params.get("l1_ratio")),
        solver="saga" if penalty != "l2" else "lbfgs",
        class_weight=None if params["class_weight"] == "none" else "balanced",
        max_iter=5000, random_state=SEED)
    scaler = RobustScaler() if params["scaler"] == "robust" else StandardScaler()
    pipe.set_params(model=clf, preprocess__num__scale=scaler)
    return pipe


def cv_macro_f1(pipe, train_df):
    return walk_forward_cv(pipe, train_df)["macro_f1"]


def plot_history(trials):
    best_so_far = np.maximum.accumulate(trials["value"].values)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.scatter(trials["number"], trials["value"], s=22, color="#3B8DEB", alpha=0.6, label="Trial CV macro-F1")
    ax.plot(trials["number"], best_so_far, color=ACCENT, lw=2.2, label="Best so far")
    ax.axhline(trials.loc[0, "value"], color="#5B6475", ls=":", label=f"Default config = {trials.loc[0, 'value']:.3f}")
    ax.set(title="Optuna search — Logistic Regression\n(walk-forward CV on training years only)",
           xlabel="Trial number", ylabel="Mean macro-F1 over 3 folds",
           ylim=(trials["value"].min() - 0.03, trials["value"].max() + 0.03))
    ax.legend(loc="center right")
    fig.tight_layout()
    fig.savefig(FIGS / "q5_optimisation_history.png", dpi=150)
    plt.close(fig)


def main():
    for d in (RESULTS, FIGS, MODELS):
        d.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(DATA / "train.csv", low_memory=False)
    val_df = pd.read_csv(DATA / "val.csv", low_memory=False)
    y_train, y_val = train_df[TARGET_COL].map(TARGET_MAP), val_df[TARGET_COL].map(TARGET_MAP)

    # ---------- Q5.1: Optuna search scored by walk-forward CV on the training years ----------
    def objective(trial):
        params = {
            "C": trial.suggest_float("C", 1e-3, 100, log=True),
            "penalty": trial.suggest_categorical("penalty", ["l2", "l1", "elasticnet"]),
            "class_weight": trial.suggest_categorical("class_weight", ["balanced", "none"]),
            "scaler": trial.suggest_categorical("scaler", ["standard", "robust"]),
        }
        if params["penalty"] == "elasticnet":
            params["l1_ratio"] = trial.suggest_float("l1_ratio", 0.05, 0.95)
        folds = cv_macro_f1(configure(params), train_df)
        trial.set_user_attr("cv_std", float(folds.std(ddof=1)))
        return float(folds.mean())

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=SEED))
    default_params = {"C": 1.0, "penalty": "l2", "class_weight": "balanced", "scaler": "standard"}
    study.enqueue_trial(default_params)  # trial 0 = the untuned Q3/Q4 configuration
    study.optimize(objective, n_trials=N_TRIALS)

    trials = study.trials_dataframe(attrs=("number", "value", "params", "user_attrs"))
    trials.to_csv(RESULTS / "q5_optuna_trials.csv", index=False)
    best_params = study.best_params
    print(f"Best CV macro-F1 = {study.best_value:.4f} with {best_params}")

    # ---------- Q5.2: pre vs post (CV folds and validation year 2022) ----------
    default_pipe, tuned_pipe = build_models()[CHAMPION], configure(best_params)
    rows = []
    for label, pipe in [("Default (Q3/Q4)", default_pipe), ("Tuned (Optuna)", tuned_pipe)]:
        folds = cv_macro_f1(pipe, train_df)
        fitted = clone(pipe).fit(train_df, y_train)
        va = score(y_val, fitted.predict(val_df), fitted.predict_proba(val_df)[:, 1])
        rows.append({"config": label, "cv_macro_f1_mean": folds.mean(),
                     "cv_macro_f1_std": folds.std(ddof=1),
                     **{f"val_{k}": v for k, v in va.items()}})
    pre_post = pd.DataFrame(rows)
    pre_post.to_csv(RESULTS / "q5_pre_post.csv", index=False)
    print("\nPre vs post optimisation:")
    print(pre_post.round(4).to_string(index=False))

    plot_history(trials)

    # ---------- Q5.3: lock, refit on 2018-2022, evaluate ONCE on 2023 ----------
    final_df = pd.concat([train_df, val_df], ignore_index=True)
    final_pipe = clone(tuned_pipe).fit(final_df, final_df[TARGET_COL].map(TARGET_MAP))
    joblib.dump(final_pipe, MODELS / "final_pipeline.joblib")

    test_df = pd.read_csv(DATA / "test.csv", low_memory=False)  # first and only time the test year is loaded
    y_test = test_df[TARGET_COL].map(TARGET_MAP)
    test_prob = final_pipe.predict_proba(test_df)[:, 1]
    test_pred = final_pipe.predict(test_df)
    test_scores = score(y_test, test_pred, test_prob)

    rule_pred = PriorOutcomeRule().fit(None, None).predict(test_df)
    rule_scores = score(y_test, rule_pred, rule_pred)

    print(f"\nLOCKED pipeline on test year 2023 (n={len(y_test)}):")
    print(classification_report(y_test, test_pred, target_names=LABELS, digits=3))
    print(f"Repeat-last-year rule on 2023: macro-F1={rule_scores['macro_f1']:.4f}")

    cm = confusion_matrix(y_test, test_pred, labels=[0, 1])
    fig, ax = plt.subplots(figsize=(5.5, 4.8))
    ConfusionMatrixDisplay(cm, display_labels=LABELS).plot(ax=ax, cmap="Blues", colorbar=False, values_format="d")
    ax.grid(False)
    ax.set(title=f"Final tuned Logistic Regression — test year 2023 (n = {len(y_test)})",
           xlabel="Predicted class (year t+1)", ylabel="Actual class (year t+1)")
    fig.tight_layout()
    fig.savefig(FIGS / "q5_test_confusion_matrix.png", dpi=150)
    plt.close(fig)

    pd.DataFrame({"demarcation.code": test_df["demarcation.code"], "Name": test_df["Name"],
                  "y_true": y_test, "champion_pred": test_pred, "champion_prob": test_prob,
                  "repeat_last_year_pred": rule_pred}).to_csv(RESULTS / "q5_test_predictions.csv", index=False)

    result = {
        "champion": CHAMPION, "search_method": "Optuna TPE (seed 42)", "n_trials": N_TRIALS,
        "search_space": SEARCH_SPACE,
        "scoring_rule": "mean macro-F1 over walk-forward folds 2019, 2020, 2021 (training years only)",
        "best_params": best_params, "best_cv_macro_f1": study.best_value,
        "final_fit_years": "2018-2022", "test_year": 2023, "n_test": int(len(y_test)),
        "test_metrics": test_scores, "repeat_last_year_test_metrics": rule_scores,
        "test_confusion": cm.tolist(),
        "pre_post": pre_post.round(4).to_dict(orient="records"),
    }
    (RESULTS / "q5_test_result.json").write_text(json.dumps(result, indent=1))
    print(f"\nSaved locked pipeline to {MODELS / 'final_pipeline.joblib'}")


if __name__ == "__main__":
    main()
