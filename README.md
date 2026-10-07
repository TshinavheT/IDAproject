# IDAproject — Data Science for Better Service Delivery in South Africa

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

## Team
| Name | Student number | Role |
|------|----------------|------|
|      |                |      |
