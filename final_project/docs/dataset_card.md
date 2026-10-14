# Dataset card: Municipal Money — municipal finance and audit outcomes

| Field | Entry |
|---|---|
| Name | Municipal Money – Municipal Finance Data |
| Owner | National Treasury, Republic of South Africa (platform run with OpenUp) |
| Source | https://municipaldata.treasury.gov.za · API documentation: https://municipaldata.treasury.gov.za/docs |
| Licence / terms | https://municipaldata.treasury.gov.za/terms — free use of website and API data for commercial and non-commercial purposes, no warranty of accuracy. Redistribution of the extracts in `data/raw` is therefore permitted, with attribution to National Treasury. |
| Collection | MFMA section 71 submissions signed off by each municipal manager and CFO ("Audited Actual" amounts); audit opinions from Auditor-General (AGSA) reports |
| Unit of analysis (raw) | municipality × financial year × line item × amount type |
| Unit of analysis (model) | one municipality in one financial year t (municipality-year), keyed by the Municipal Demarcation Board code |
| Target | AGSA opinion for year t+1: **at_risk** = qualified, adverse, disclaimer or outstanding; **not_at_risk** = unqualified (with or without findings) |
| Modelling rows | 1,434 municipality-years, feature years 2018–2023, 257 municipalities; plus 245 forecast rows for 2024 → 2025 |
| Class balance | 54.5% not_at_risk, 45.5% at_risk (2022 validation year: 42.2% at risk) |
| Split | Time-based: train 2018–2021 (950), validation 2022 (244), test 2023 (240, used once) |
| Personal data | None. The Municipal Officials dataset and all contact fields were excluded at download (POPIA). |
| Sensitive attributes | Province and municipality type (metro, district, local) act as proxies for rurality and poverty. They are **not** model inputs; they are used only to check fairness (see Q8.1). |

## Raw extracts in `data/raw`

| File | Municipal Money dataset (API cube) | Used for | Years | Municipalities |
|---|---|---|---|---|
| `incexp_audited_all.csv` | Income and Expenditure (`incexp_v2`) | revenue, expenditure, property rates, service charges, debt impairment | 2018–2025 | 257 |
| `finpos_audited_all.csv` | Financial Position (`financial_position_v2`) | cash and cash equivalents | 2018–2025 | 257 |
| `debtor_audited_all.csv` | Aged Debtor Analysis (`aged_debtor_v2`) | total debtors | 2020–2025 | 255 |
| `repmaint_audited_all.csv` | Repairs and Maintenance (`repmaint_v2`) | repairs and maintenance spending | 2019–2025 | 256 |
| `uifwexp_audited_all.csv` | Unauthorised, Irregular, Fruitless and Wasteful Expenditure (`uifwexp`) | irregular expenditure | 2018–2024 | 257 |
| `grants_audited_all.csv` | Grants (`grants_v2`) | grants received | 2020–2024 | 182 |
| `cflow_audited_all.csv`, `creditor_audited_all.csv` | Cash Flow (`cflow_v2`), Aged Creditor (`aged_creditor_v2`) | downloaded, not used in the final features | 2018/2020–2025 | 257 / 256 |
| `audit_opinion_facts.csv` | Audit Opinions (with links to each AGSA report) | target (t+1) and prior outcome (t) | 2011–2024 | 292 |

## Known limitations

1. **Data is only as reliable as each municipality's submission.** Some values are implausible (for example cash coverage of −23.7 months or irregular expenditure of 1,271% of expenditure); they are kept as reported and flagged by the app.
2. **Missing items are recorded as 0, not as missing.** Debtor data starts in 2020 and repairs data in 2019, so `debtor_days` and `repairs_maintenance_ratio` are 0 for earlier years.
3. **The grants extract appears truncated** at exactly 100,000 rows and covers only 182 municipalities, so `grant_dependency` is incomplete. The final model gives it a coefficient of 0.
4. **Chart of accounts change (mSCOA, 2019-20)** and the 2016 boundary changes alter line-item codes and municipalities over time.
5. **Non-submitters are the highest-risk municipalities but have the least data.** Municipalities without audited figures for a year are absent from that year.
