# Predicting Municipal Audit Outcomes — IDA117V Group Project (S2 2026)

Predict, one audit cycle ahead, whether each South African municipality will receive a poor
Auditor-General (AGSA) outcome (qualified, adverse, disclaimer or outstanding), so National Treasury
can direct financial-management support before failure rather than after.

- **Unit of prediction:** one municipality in one financial year (t), predicting the audit outcome of year t+1
- **Target:** `at_risk` vs `not_at_risk`
- **Champion:** tuned Logistic Regression (L1), fit on 2018–2022, tested once on 2023
- **App:** Streamlit KPI dashboard with risk check, model evidence and responsible-use notes

## Data source and licence
National Treasury, *Municipal Money* — https://municipaldata.treasury.gov.za
(API documentation: https://municipaldata.treasury.gov.za/docs). Datasets used: Income and Expenditure,
Financial Position, Aged Debtor Analysis, Repairs and Maintenance, Unauthorised/Irregular/Fruitless and Wasteful
Expenditure, Grants and Audit Opinions (details, years and coverage in [docs/dataset_card.md](docs/dataset_card.md)).

The [Municipal Money Terms of Use](https://municipaldata.treasury.gov.za/terms) allow free commercial and
non-commercial use of the website and API data, so the extracts are included in `data/raw` with attribution to
National Treasury. No personal data is used: the Municipal Officials dataset and all contact fields are excluded.

## Structure
```
data/raw/            Municipal Money extracts (finances, debtors, repairs, irregular expenditure, grants, audit opinions)
data/processed/      modeling_dataset.csv and the time-based train/val/test splits
src/                 one script per report question (see Execution order) + shared models.py, neural.py
models/              final_pipeline.joblib (locked champion used by the app) and models/q3/ (Q3 fits)
results/             metric tables, predictions (incl. paired McNemar predictions) and JSON summaries
reports/             report sections (.docx), figures, data audit; build/capture scripts for the report
docs/                dataset card, data dictionary, experiment log
app/                 Streamlit dashboard, sample CSVs (app/samples) and smoke test (app/test_app.py)
notebooks/archive/   first Question 3 run (random split), superseded and kept for the record
run_all.py           reproduces every result in order
```

## Setup
Python 3.12.
```bash
python -m venv .venv
.venv\Scripts\activate                 # Windows  (source .venv/bin/activate on macOS/Linux)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

## Reproduce everything
```bash
python run_all.py              # uses the cached data in data/raw (about 10 minutes on a laptop CPU)
python run_all.py --download   # first re-downloads data/raw from the Municipal Money API
```
All randomness uses seed 42 (`src/models.py`). There are no manual steps, secrets or local paths: every script
finds its files relative to the project folder. `run_all.py` runs, in order:

| Step | Script | Report question |
|---|---|---|
| (optional) | `src/build_modeling_dataset.py` — download the cubes and build the modelling dataset | Q2 |
| 1 | `src/audit_q21_v2.py` — data audit → `reports/data_dictionary.csv`, `reports/audit_report.txt` | Q2.1 |
| 2 | `src/visualize_q22_v2.py` — five EDA figures | Q2.2 |
| 3 | `src/split_q23_v2.py` — time split: train 2018–2021, validation 2022, test 2023 | Q2.3 |
| 4 | `src/pipeline_q24.py` — preprocessing fit on training rows only | Q2.4 |
| 5 | `src/train_q3.py` — baselines and the four models | Q3 |
| 6 | `src/evaluate_q4.py` — metrics, ROC/PR, CV, overfitting | Q4 |
| 7 | `src/optimise_q5.py` — Optuna tuning and the **only** use of the 2023 test year | Q5 |
| 8 | `src/ablation_mcnemar_q6.py` — ablations and McNemar's test | Q6 |
| 9 | `src/forecast_next.py` — score every municipality-year and forecast the 2025 audit | Q7 |
| 10 | `src/fairness_q8.py` — bootstrap confidence intervals, calibration, fairness by province and type | Q8 |
| 11 | `src/experiment_log.py` — regenerate `docs/experiment_log.md` | Q8 |

Report documents: `node reports/build_report_sections.js` rebuilds the Q4–Q8 report sections and `node reports/build_contribution_statement.js` the contribution statement; with the app running,
`node reports/capture_app_screenshots.js` refreshes the dashboard screenshots (headless Microsoft Edge).

## Live demo and deployment
- **Live dashboard:** _link added after deployment_ (Streamlit Community Cloud)
- **Presentation slides:** https://claude.ai/artifact/Kp9praEutWvN9bFA9tCMPU (open from the owner's Share menu)

The dashboard is deployed on [Streamlit Community Cloud](https://share.streamlit.io) straight from GitHub:
1. Sign in at https://share.streamlit.io with the GitHub account that owns the repository.
2. **Create app** → *Deploy a public app from GitHub* → repository `TshinavheT/IDAproject`, branch `main`,
   main file path `final_project/app/app.py`.
3. **Advanced settings** → Python **3.12** → **Deploy**.

It installs only `app/requirements.txt` (no PyTorch: the app loads the saved Logistic Regression pipeline), so the
build takes a few minutes. Every push to `main` redeploys the app automatically.

## Launch the dashboard
```bash
streamlit run app/app.py
```
Then open http://localhost:8501. Pages:
- **Overview** — test-year KPIs and the 2025 forecast. Every ring and gauge has a *Details* / *See list* drill-down;
  click a trend point for that year's breakdown, a top-10 bar to open the municipality, a province to explore it,
  or a leaderboard bar for that model's details
- **Explorer** — filter by audit year (2019–2025), province, type (metro/district/local), last audit opinion and
  risk band; click a category bar to filter, a table row or a riser to open the municipality
- **Municipality profile** (`/municipality?code=GT421`) — 2025 forecast with reasons and national/province rank,
  risk history 2019–2025 against actual outcomes, audit-opinion timeline, six financial-health trends against the
  national median, and peer comparison against Treasury norms
- **Risk check** — pick a municipality, enter figures, or upload a CSV; returns the class, probability and a
  plain-language explanation
- **Model evidence** — ROC curves, CV stability, confusion matrix, ablations, McNemar test, tuning, overfitting
- **About & responsible use** — purpose, limitations, data licence and when not to use the model

Demo files for Q7.4 are in `app/samples/`: `valid_cases.csv` (3 valid municipalities) and
`invalid_case.csv` (rejected with clear error messages).

## Team
| Name | Student number | Role |
|------|----------------|------|
|      |                |      |
