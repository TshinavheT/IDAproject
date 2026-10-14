"""
Q3 re-run on the Q2.3 time-based split.
Run from the project root:  python src/train_q3.py

Fixes relative to the first Q3 notebook:
  1. Uses the time-based split from Q2.3 (train 2018-2021, validation 2022,
     test 2023) instead of a new random 70/15/15 split.
  2. Does NOT touch the test year. The test set is used once, in Q5.3, on the
     final tuned champion only.
  3. Uses only the Q2.4 feature list, so financial_year_end.year, identifiers
     and the raw opinion columns cannot enter the models.

Saves:
  results/q3_validation_metrics.csv   train + validation metrics per model
  results/q3_val_predictions.csv      validation predictions/probabilities per model
  models/q3/<model>.joblib            fitted pipelines (reused in Q4)
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, average_precision_score, f1_score,
                             precision_score, recall_score, roc_auc_score)

from models import BASELINES, build_models
from pipeline_q24 import CATEGORICAL_FEATURES, NUMERIC_FEATURES, load_split

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS = PROJECT_ROOT / "results"
MODEL_DIR = PROJECT_ROOT / "models" / "q3"


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


def main():
    RESULTS.mkdir(exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    X_train, y_train = load_split("train")
    X_val, y_val = load_split("val")
    print("Features used:", NUMERIC_FEATURES + CATEGORICAL_FEATURES)
    print(f"Train rows: {len(X_train)} | Validation rows: {len(X_val)} | Test: not loaded")

    rows, val_preds = [], {"y_true": y_val.values}
    for name, pipe in build_models().items():
        pipe.fit(X_train, y_train)

        tr_prob = pipe.predict_proba(X_train)[:, 1]
        va_prob = pipe.predict_proba(X_val)[:, 1]
        tr_pred, va_pred = pipe.predict(X_train), pipe.predict(X_val)

        tr, va = score(y_train, tr_pred, tr_prob), score(y_val, va_pred, va_prob)
        row = {"model": name, **{f"val_{k}": v for k, v in va.items()},
               **{f"train_{k}": v for k, v in tr.items()}}
        clf = getattr(pipe, "named_steps", {}).get("model", pipe)
        if hasattr(clf, "best_epoch_"):
            row["best_epoch"], row["epochs_run"] = clf.best_epoch_, clf.n_epochs_run_
        rows.append(row)

        val_preds[f"{name}__pred"] = va_pred
        val_preds[f"{name}__prob"] = va_prob
        joblib.dump(pipe, MODEL_DIR / f"{name.replace(' ', '_').replace('(', '').replace(')', '')}.joblib")
        print(f"{name:22s} val acc={va['accuracy']:.4f}  val macro-F1={va['macro_f1']:.4f}  "
              f"val ROC-AUC={va['roc_auc']:.4f}")

    metrics = pd.DataFrame(rows)
    metrics.to_csv(RESULTS / "q3_validation_metrics.csv", index=False)
    preds = pd.DataFrame(val_preds)
    preds.to_csv(RESULTS / "q3_val_predictions.csv", index=False)

    substantive = metrics[~metrics["model"].isin(BASELINES)]
    champion = substantive.sort_values("val_macro_f1", ascending=False).iloc[0]["model"]
    print(f"\nProvisional champion (highest validation macro-F1): {champion}")

    # Do the models just copy last year's audit outcome? Compare with that rule.
    prior_rule = (X_val["prior_audit_outcome"] == "at_risk").astype(int).values
    print("\nAgreement with the 'repeat last year's outcome' rule on validation:")
    for name in substantive["model"]:
        agree = np.mean(preds[f"{name}__pred"].values == prior_rule)
        print(f"  {name:22s} {agree:.1%}")
    print(f"  Rule itself: acc={accuracy_score(y_val, prior_rule):.4f}  "
          f"macro-F1={f1_score(y_val, prior_rule, average='macro'):.4f}")


if __name__ == "__main__":
    main()
