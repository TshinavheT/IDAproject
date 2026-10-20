"""
Builds and executes the project notebooks, one per question of the technical report.
Each notebook calls the same code as run_all.py (src/), so its numbers match the report exactly,
and is saved with its outputs. Run from the project root:

    python notebooks/build_notebooks.py            # build and execute all notebooks
    python notebooks/build_notebooks.py --no-run   # build without executing
    python notebooks/build_notebooks.py 06_Q7_forecast_and_dashboard   # only the named notebook(s)

Needs nbformat, nbclient and ipykernel (pip install nbformat nbclient ipykernel).
"""

import sys
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).resolve().parent
KERNEL = {"name": "python3", "display_name": "Python 3"}

SETUP = '''import sys, json, logging, warnings
from pathlib import Path
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)
pd.set_option("display.max_columns", 40)
pd.set_option("display.width", 180)
pd.set_option("display.float_format", "{:.3f}".format)
RESULTS, FIGS = ROOT / "results", ROOT / "reports" / "figures"
show = lambda name, width=800: display(Image(filename=str(FIGS / name), width=width))'''


def md(text):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text):
    return nbf.v4.new_code_cell(text.strip())


NOTEBOOKS = {}

# ---------------------------------------------------------------------------------------------- Q1-Q2
NOTEBOOKS["01_Q1_Q2_problem_data_and_pipeline"] = [
    md("""
# Notebook 1 · Questions 1 and 2: problem, data audit, visualisation, split and pipeline
**IDA117V group project (group Auditors): predicting municipal audit outcomes one audit cycle ahead.**
This notebook follows Questions 1 and 2 of the technical report (`reports/IDA117V_Technical_Report.pdf`).
It runs the same scripts as `run_all.py`, so every number matches the report.
"""),
    md("""
## Question 1: the problem in brief
* **Problem.** The Auditor-General (AGSA) audits all 257 municipalities each year, but the result arrives long after the financial year
  ends, so National Treasury usually responds after the damage is done.
* **Decision-maker.** National Treasury's local government support function and the provincial treasuries, who decide where to send
  financial-management support.
* **Classification task.** Unit: one municipality in financial year *t*. Inputs: nine audited financial indicators for year *t* plus the
  year *t* audit outcome. Target: the AGSA outcome for year *t+1*, **at_risk** (qualified, adverse, disclaimer, outstanding) or
  **not_at_risk** (unqualified, with or without findings). Horizon: one audit cycle.
* **Primary metric:** macro-F1 (both classes count equally); recall and precision for *at_risk* are the service-delivery indicators.
* **Data:** National Treasury's *Municipal Money* (free to reuse, no personal data). Full card: `docs/dataset_card.md`.
"""),
    code(SETUP),
    code('''df = pd.read_csv(ROOT / "data" / "processed" / "modeling_dataset.csv")
print("Rows:", len(df), "| municipalities:", df["demarcation.code"].nunique(), "| feature years:", sorted(df["financial_year_end.year"].unique()))
display(df.head())
display(df["target_next_year"].value_counts().to_frame("records").assign(share=lambda t: t.records / t.records.sum()))'''),
    md("## 2.1 Data dictionary and data audit\nThe audit script writes the data dictionary and the audit report (missing values, duplicates, invalid values, 3 × IQR outliers, leakage)."),
    code('''import audit_q21_v2
audit_q21_v2.main()
display(pd.read_csv(ROOT / "reports" / "data_dictionary.csv"))'''),
    code('''print((ROOT / "reports" / "audit_report.txt").read_text())'''),
    md("""
**Leakage check.** All inputs describe year *t* and the target is year *t+1*; identifiers, the year and the raw opinion of *t+1* are
excluded; preprocessing is learned on training rows only. `prior_audit_outcome` (the year *t* result) is past information, so it is
not leakage, but it is a strong "repeat last year" signal; its effect is measured in Questions 3, 4 and 6.
"""),
    md("## 2.2 Visualisations\nFive figures, each with a title, units and labels; the interpretations are in the report (section 2.2)."),
    code('''import visualize_q22_v2
visualize_q22_v2.main()
for name in ["01_target_distribution.png", "02_missingness_by_feature.png", "03_surplus_vs_risk.png",
             "04_debtordays_vs_risk.png", "05_risk_trend_by_year.png"]:
    show(name, 560)'''),
    code('''# Numbers quoted in the interpretations of Figures 3 and 4
g = df.groupby("target_next_year")
display((g["operating_surplus"].quantile([0.25, 0.5, 0.75]).unstack() / 1e6).rename(columns=lambda q: f"surplus Q{q} (R m)"))
display(g["debtor_days"].quantile([0.25, 0.5, 0.75]).unstack().rename(columns=lambda q: f"debtor days Q{q}"))'''),
    md("## 2.3 Time-based train, validation and test split\nSplit by feature year before any transformation is learned: train 2018–2021, validation 2022, test 2023 (used once, in Question 5.3)."),
    code('''import split_q23_v2
split_q23_v2.main()
splits = {name: pd.read_csv(ROOT / "data" / "processed" / f"{name}.csv") for name in ["train", "val", "test"]}
display(pd.DataFrame({name: {"years": f"{s['financial_year_end.year'].min()}–{s['financial_year_end.year'].max()}", "records": len(s),
                             "at_risk": int((s.target_next_year == "at_risk").sum()),
                             "at_risk share": round((s.target_next_year == "at_risk").mean(), 3)}
                      for name, s in splits.items()}).T)'''),
    md("## 2.4 Preparation pipeline\nOne scikit-learn `ColumnTransformer` (median imputation and scaling for the nine numbers, most-frequent imputation and one-hot encoding for `prior_audit_outcome`), fitted on the training split only."),
    code('''import pipeline_q24
pipeline_q24.main()
print("Numeric features:", pipeline_q24.NUMERIC_FEATURES)
print("Categorical features:", pipeline_q24.CATEGORICAL_FEATURES)
pipeline_q24.build_pipeline()'''),
]

# ---------------------------------------------------------------------------------------------- Q3 (updated team notebook)
NOTEBOOKS["02_Q3_baselines_and_models"] = [
    md("""
# Notebook 2 · Question 3: baseline and models
*Updated version of the team's first Question 3 notebook (P Khosa, `Baseline&Models.ipynb`; the original is kept in `notebooks/archive/`).*
The structure is the same (baseline, four models, comparison), with three corrections so it matches the rest of the project:
1. it uses the **time-based split** of Question 2.3 (train 2018–2021, validation 2022) instead of a random 70/15/15 split;
2. the **test year is not used** here (it is used once, in Question 5.3);
3. only the Question 2.4 features are inputs (`financial_year_end.year` and the raw opinion columns are excluded).
"""),
    code(SETUP),
    code('''from sklearn.base import clone
from pipeline_q24 import load_split, NUMERIC_FEATURES, CATEGORICAL_FEATURES
from models import build_models, BASELINES, SEED
from train_q3 import score

X_train, y_train = load_split("train")
X_val, y_val = load_split("val")
print("Inputs:", NUMERIC_FEATURES + CATEGORICAL_FEATURES)
print(f"Train {X_train.shape} | validation {X_val.shape} | seed {SEED}")'''),
    md("""
## 3.1 Baselines
* **Dummy (most frequent):** predicts *not_at_risk* for everyone; sets the floor.
* **Repeat last year's outcome:** predicts that year *t+1* repeats year *t*; shows how much skill comes from audit persistence alone.
Neither counts among the four substantive models.
## 3.2–3.3 Four models on identical data
Two traditional models (Logistic Regression, Random Forest) and two neural networks (an MLP and a residual tabular network), all inside the
same preprocessing pipeline and trained on the same rows with seed 42.
"""),
    code('''models = build_models()
fitted, rows = {}, []
for name, model in models.items():
    m = clone(model).fit(X_train, y_train)
    fitted[name] = m
    va = score(y_val, m.predict(X_val), m.predict_proba(X_val)[:, 1])
    rows.append({"model": name, "family": "baseline" if name in BASELINES else
                 ("neural" if name in ("MLP", "Residual Tabular NN") else "traditional"), **va})
results = pd.DataFrame(rows).set_index("model")
results'''),
    code('''# How often does each model agree with the "repeat last year" rule on the validation year?
rule = (X_val["prior_audit_outcome"] == "at_risk").astype(int).to_numpy()
pd.Series({n: (fitted[n].predict(X_val) == rule).mean() for n in models if n not in BASELINES}, name="agreement with rule")'''),
    md("## 3.4 Architecture, hyper-parameters and training details"),
    code('''for name, model in models.items():
    clf = model.named_steps["model"] if hasattr(model, "named_steps") else model
    params = {k: v for k, v in clf.get_params().items() if v is not None and v != "deprecated"}
    print(f"{name}: {type(clf).__name__} {params}")
for name in ["MLP", "Residual Tabular NN"]:
    clf = fitted[name].named_steps["model"]
    print(f"{name}: best epoch {clf.best_epoch_}, stopped at epoch {clf.n_epochs_run_} (early stopping, patience {clf.patience})")'''),
    md("""
## 3.5 Rationale
Logistic Regression suits fewer than 1,000 rows and nine ratios: stable and explainable. Random Forest captures non-linear effects and is
robust to heavy-tailed values but can memorise. The MLP tests whether a flexible model extracts more from the ratios; the residual network
tests whether extra depth with a skip connection helps. **Result:** all four beat the dummy baseline clearly, but the "repeat last year" rule
already reaches macro-F1 0.887, and Logistic Regression is the provisional champion (Question 4.3).
"""),
]

# ---------------------------------------------------------------------------------------------- Q4
NOTEBOOKS["03_Q4_evaluation_and_overfitting"] = [
    md("# Notebook 3 · Question 4: evaluation, comparison and overfitting\nRuns `src/evaluate_q4.py`: every model is fit on 2018–2021 and evaluated on the same 244 municipalities of 2022."),
    code(SETUP),
    code('''import evaluate_q4
evaluate_q4.main()'''),
    md("## 4.1 Held-out metrics for every model"),
    code('''q4 = pd.read_csv(RESULTS / "q4_validation_metrics.csv").set_index("model")
q4[[c for c in q4.columns if c.startswith("val_")]]'''),
    md("## 4.2 Classification reports, confusion matrices and ROC curves"),
    code('''print((RESULTS / "q4_classification_reports.txt").read_text())'''),
    code('''show("q4_confusion_matrices.png", 900)
show("q4_roc_curves.png", 520)
show("q4_pr_curves.png", 520)'''),
    md("## 4.3 Comparison and provisional champion (validation and walk-forward cross-validation)"),
    code('''cv = pd.read_csv(RESULTS / "q4_cv_walk_forward.csv").set_index("model")
display(cv)
show("q4_model_comparison.png", 900)
print("Provisional champion (validation macro-F1, ties broken by ROC-AUC):",
      json.loads((RESULTS / "dashboard_q4.json").read_text())["champion"])'''),
    md("## 4.4 Overfitting: train–validation gap, learning curves and neural training curves"),
    code('''display(pd.read_csv(RESULTS / "q4_overfitting_gap.csv").set_index("model"))
show("q4_learning_curves.png", 900)
show("q4_neural_training_curves.png", 800)'''),
]

# ---------------------------------------------------------------------------------------------- Q5
NOTEBOOKS["04_Q5_champion_optimisation"] = [
    md("""
# Notebook 4 · Question 5: champion optimisation and the one-time test
Runs `src/optimise_q5.py`: Optuna (TPE, seed 42, 60 trials) tunes Logistic Regression on walk-forward cross-validation inside the training
years; the tuned pipeline is locked, refit on 2018–2022 and evaluated **once** on the 2023 test year.
"""),
    code(SETUP),
    code('''import optimise_q5
optimise_q5.main()'''),
    md("## 5.1 Search space, scoring rule and search history"),
    code('''q5 = json.loads((RESULTS / "q5_test_result.json").read_text())
print("Search:", q5["search_method"], "|", q5["n_trials"], "trials")
print("Scoring rule:", q5["scoring_rule"])
display(pd.Series(q5["search_space"], name="range"))
trials = pd.read_csv(RESULTS / "q5_optuna_trials.csv").sort_values("value", ascending=False)
display(trials.head(5))
show("q5_optimisation_history.png", 700)'''),
    md("## 5.2 Before and after optimisation (cross-validation and validation year)"),
    code('''display(pd.DataFrame(q5["pre_post"]).set_index("config"))
print("Chosen hyper-parameters:", q5["best_params"])
import joblib
pipe = joblib.load(ROOT / "models" / "final_pipeline.joblib")
names = pipe.named_steps["preprocess"].get_feature_names_out()
pd.Series(pipe.named_steps["model"].coef_[0], index=names, name="coefficient").sort_values(key=abs, ascending=False)'''),
    md("## 5.3 The locked pipeline on the 2023 test year (used once)"),
    code('''display(pd.DataFrame({"locked model": q5["test_metrics"], "repeat-last-year rule": q5["repeat_last_year_test_metrics"]}))
print("Confusion matrix [[TN, FP], [FN, TP]]:", q5["test_confusion"])
show("q5_test_confusion_matrix.png", 420)
pred = pd.read_csv(RESULTS / "q5_test_predictions.csv")
print("Agreement with the repeat-last-year rule on the test year:", (pred.champion_pred == pred.repeat_last_year_pred).mean())'''),
]

# ---------------------------------------------------------------------------------------------- Q6
NOTEBOOKS["05_Q6_ablation_and_mcnemar"] = [
    md("# Notebook 5 · Question 6: ablation study and McNemar's test\nRuns `src/ablation_mcnemar_q6.py`. Each ablation changes one component with the split, seed and protocol fixed; McNemar's test compares the champion and the MLP on the same 2023 municipalities."),
    code(SETUP),
    code('''import ablation_mcnemar_q6
ablation_mcnemar_q6.main()'''),
    md("## 6.1 Controlled ablations"),
    code('''abl = pd.read_csv(RESULTS / "q6_ablation.csv").set_index("experiment")
display(abl[["val_macro_f1", "delta_val_macro_f1", "val_roc_auc", "delta_val_roc_auc", "val_recall_at_risk", "cv_macro_f1_mean"]])
show("q6_ablation.png", 760)'''),
    md("## 6.2 McNemar's test (H₀: equal error rates; α = 0.05; exact binomial when b + c < 25)"),
    code('''mc = json.loads((RESULTS / "q6_mcnemar.json").read_text())
t = mc["table"]
display(pd.DataFrame([[t["both_correct"], t["champion_only_correct"]], [t["comparator_only_correct"], t["both_wrong"]]],
                     index=["champion correct", "champion wrong"], columns=["MLP correct", "MLP wrong"]))
print(mc["test_version"], "| statistic =", mc["statistic"], "| p =", round(mc["p_value"], 4), "| reject H0:", mc["reject_H0"])
show("q6_mcnemar_table.png", 480)'''),
]

# ---------------------------------------------------------------------------------------------- Q7
NOTEBOOKS["06_Q7_forecast_and_dashboard"] = [
    md("""
# Notebook 6 · Question 7: the 2025 forecast and the dashboard
Runs `src/forecast_next.py` (scores every municipality-year with the locked pipeline and forecasts the 2025 audit from 2024 figures), then
uses the dashboard's own prediction code (`app/core.py`) on the demonstration files. The dashboard itself is launched with
`streamlit run app/app.py`; the screenshots below are captures of the current app.
"""),
    code(SETUP),
    code('''import forecast_next
forecast_next.main()
scores = pd.read_csv(RESULTS / "municipality_scores.csv")
fc = scores[scores.split == "forecast"]
print(f"2025 forecast: {len(fc)} municipalities, {(fc.predicted_outcome == 'at_risk').sum()} flagged at risk, "
      f"{(fc.risk_probability >= 0.8).sum()} at 80% or more")
fc.sort_values("risk_probability", ascending=False)[["Name", "demarcation.code", "province", "category",
                                                     "prior_audit_opinion_raw", "risk_probability"]].head(10)'''),
    md("## 7.2–7.4 The dashboard's prediction code on the demonstration cases (three valid, one invalid)"),
    code('''sys.path.insert(0, str(ROOT / "app"))
import core
for f in ["valid_cases.csv", "invalid_case.csv"]:
    raw = pd.read_csv(ROOT / "app" / "samples" / f, dtype=str)
    clean, errors, warns, valid = core.validate(raw)
    print(f"--- {f}: {int(valid.sum())} of {len(raw)} rows valid")
    for e in errors: print("  ERROR:", e)
    for w in warns: print("  warning:", w)
    if valid.any():
        prob, label = core.predict(clean[valid])
        display(pd.DataFrame({"municipality": clean[valid]["Name"], "risk": prob.round(3), "prediction": label}))'''),
    code('''row = fc[fc["demarcation.code"] == "GT421"]
prob, label = core.predict(row)
print(f"Emfuleni 2025 forecast: {prob[0]:.1%} ({label[0]})")
for line in core.plain_language(prob[0], label[0], core.explain(row)):
    print(" -", line.replace("<b>", "").replace("</b>", "").replace('<span class="up">', "").replace('<span class="down">', "").replace("</span>", ""))'''),
    md("## Screenshots of the dashboard (current version)"),
    code('''for name in ["app_overview_full.png", "app_risk_check_result.png", "app_invalid_input.png", "app_profile_top.png",
             "app_explorer.png", "app_dialog_recall.png"]:
    print(name); show("app/" + name, 760)'''),
]

# ---------------------------------------------------------------------------------------------- Q8
NOTEBOOKS["07_Q8_uncertainty_fairness_and_recommendation"] = [
    md("# Notebook 7 · Question 8: uncertainty, fairness, recommendation and reproducibility\nRuns `src/fairness_q8.py` (bootstrap intervals, calibration, performance by province and type on the test year) and `src/experiment_log.py`."),
    code(SETUP),
    code('''import fairness_q8, experiment_log
fairness_q8.main()
experiment_log.main()'''),
    md("## Uncertainty and calibration"),
    code('''q8 = json.loads((RESULTS / "q8_uncertainty.json").read_text())
display(pd.DataFrame(q8["metrics_ci95"]).T)
print("Brier score:", round(q8["brier_score"], 3))
print(f"Status changes in the test year: {q8['status_changes_in_test']} (accuracy on them {q8['accuracy_on_status_changes']:.0%}, "
      f"on stable municipalities {q8['accuracy_on_stable']:.0%})")
print("2025 forecast:", q8["forecast_2025"])
show("q8_calibration.png", 420)'''),
    md("## Fairness by province and municipality type"),
    code('''display(pd.read_csv(RESULTS / "q8_fairness_province.csv"))
display(pd.read_csv(RESULTS / "q8_fairness_type.csv"))
show("q8_fairness.png", 900)'''),
    md("""
## 8.1 Recommendation
Use the model as a **consistent, explainable triage list for municipalities already in difficulty**, not as an early-warning system:
its decisions equal "repeat last year's outcome", it misclassifies every municipality whose status changes, and false alarms are uneven
across provinces (review flagged lists by province). Monitor yearly against the published AGSA outcomes and retrain if macro-F1 falls
below the lower confidence bound. Never use it to allocate funding automatically or to penalise municipalities.
## 8.2 Reproducibility
`python run_all.py` reproduces every result (seed 42, pinned `requirements.txt`); the experiment log is regenerated below.
"""),
    code('''print((ROOT / "docs" / "experiment_log.md").read_text()[:3000])'''),
]


def build(run=True):
    from nbclient import NotebookClient
    only = [a for a in sys.argv[1:] if not a.startswith("--") and a in NOTEBOOKS]
    for name, cells in NOTEBOOKS.items():
        if only and name not in only:
            continue
        nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {**KERNEL, "language": "python"},
                                                        "language_info": {"name": "python"}})
        path = HERE / f"{name}.ipynb"
        if run:
            print("executing", path.name, flush=True)
            NotebookClient(nb, timeout=900, kernel_name=sys.argv[sys.argv.index("--kernel") + 1] if "--kernel" in sys.argv else "python3",
                           resources={"metadata": {"path": str(HERE)}}).execute()
        nbf.write(nb, path)
        print("wrote", path.name, flush=True)


if __name__ == "__main__":
    build(run="--no-run" not in sys.argv)
