# IDAproject — Data Science for Better Service Delivery in South Africa

> **Latest complete version:** see [`final_project/`](final_project/README.md) — the corrected Question 3,
> Questions 4–8, the dashboard (`final_project/app/`), report sections and the reproducible pipeline
> (`python run_all.py`). The original Question 2 work below is unchanged.
>
> **Notebooks:** one executed notebook per report question is in [`final_project/notebooks/`](final_project/notebooks)
> (`01_Q1_Q2` … `07_Q8`). `Baseline&Models.ipynb` in this folder has been updated to the corrected Question 3
> (time-based split); the original is kept at `final_project/notebooks/archive/Q3_first_run_random_split.ipynb`.

IDA117V Introduction to Data Science group project (S2 2026).

**Central challenge:** How can responsible data science help a South African public-service stakeholder identify need, prioritise limited resources, or improve the reliability and reach of a service?

## Structure
```
data/raw/          original dataset (not committed if the licence forbids it)
data/processed/    cleaned / split data
notebooks/         01_eda → 02_preprocess → 03_models → 04_eval → 05_tune → 06_ablation_mcnemar
src/               reusable pipeline, training and evaluation code
models/            saved final pipeline (final_pipeline.joblib)
app/               Streamlit user interface
reports/figures/   EDA, ROC, confusion matrices, learning curves, ablation plots
docs/              concept note, dataset card, data dictionary, contribution statement
```

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Execution order
_To be completed: run notebooks 01 → 06, then launch the app._

```bash
streamlit run app/app.py
```

## Data source
_To be completed: dataset URL, owner, licence._

## Team: Auditors
| Name | Student number |
|------|----------------|
| T Chaba | 216089898 |
| R Tabohane | 217033101 |
| T Mabena | 221641221 |
| T Tshinavhe | 219537948 |
| P Khosa | 221335970 |

Final report: [`final_project/reports/IDA117V_Technical_Report.pdf`](final_project/reports/IDA117V_Technical_Report.pdf)
