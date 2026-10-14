# Data dictionary

Modelling dataset: `data/processed/modeling_dataset.csv` (one row per municipality-year; features from year t,
target from year t+1). Built by `src/build_modeling_dataset.py` (`engineer_features()`); audited by
`src/audit_q21_v2.py`, which also writes the column-level statistics to `reports/data_dictionary.csv`
(type, missing %, unique values).

## Model inputs (10)

| Column | Definition | Unit | Source dataset | Missing |
|---|---|---|---|---|
| `total_revenue` | Sum of operating revenue line items (mSCOA codes below 2900) | rand | Income and Expenditure | 0% |
| `total_expenditure` | Sum of operating expenditure line items (codes 3000–4399) | rand | Income and Expenditure | 0% |
| `operating_surplus` | total_revenue − total_expenditure (negative = deficit) | rand | derived | 0% |
| `cash_coverage_ratio` | Cash and cash equivalents ÷ (total_expenditure ÷ 12) | months | Financial Position, Income and Expenditure | 0.1% |
| `collection_rate` | (Property rates + service charges − debt impairment) ÷ (property rates + service charges) | fraction (0.95 = 95%) | Income and Expenditure | 8.4% |
| `debtor_days` | Total debtors ÷ (total_revenue ÷ 365) | days | Aged Debtor Analysis | 0% (0 before 2020) |
| `repairs_maintenance_ratio` | Repairs and maintenance spending ÷ total_expenditure | fraction | Repairs and Maintenance | 0.1% (0 before 2019) |
| `irregular_expenditure_ratio` | Irregular expenditure ÷ total_expenditure | fraction | UIFW Expenditure | 0.1% |
| `grant_dependency` | Grants received ÷ total_revenue | fraction | Grants (extract incomplete) | 0% |
| `prior_audit_outcome` | AGSA outcome for year t, grouped as at_risk / not_at_risk | category | Audit Opinions | 0% |

Missing numeric values are imputed with the training-year median and categories with the most frequent value,
inside the pipeline (fit on training rows only).

## Target and identifiers (not model inputs)

| Column | Definition |
|---|---|
| `target_next_year` | **Target.** AGSA outcome for year t+1: at_risk (qualified, adverse, disclaimer, outstanding) or not_at_risk (unqualified, with or without findings) |
| `target_opinion_raw` | The raw AGSA opinion for year t+1 (excluded to prevent leakage) |
| `prior_audit_opinion_raw` | The raw AGSA opinion for year t (shown in the app; the model uses the grouped `prior_audit_outcome`) |
| `demarcation.code` | Municipal Demarcation Board code (e.g. GT421) |
| `Name` | Municipality name |
| `financial_year_end.year` | Financial year t (used only to split the data; excluded from the model) |

## Added in `results/municipality_scores.csv` (dashboard and Q8)

| Column | Definition |
|---|---|
| `audit_year` | t + 1, the audit being predicted |
| `split` | fitted (2018–2022, in-sample), test (2023, held out) or forecast (2024 → 2025, outcome unknown) |
| `risk_probability` | Locked model's probability of an at_risk outcome |
| `predicted_outcome` | at_risk if `risk_probability` ≥ 0.5 |
| `actual_next_outcome`, `actual_next_opinion_raw` | Published outcome for t+1 (empty for the forecast year) |
| `province`, `category` | Province and municipality type (Metro, District, Local) derived from the demarcation code; used for fairness checks, not as inputs |
