# Report merge notes

`reports/IDA117V_Technical_Report.pdf` (and the editable `.docx`) merges Questions 1–8 into one report that follows the
project template: cover, the questions in order (1.1 to 8.3), references, appendices. The teammates' original files are
**unchanged** in `reports/` (`IDA117V_Q1.docx`, `Question2_Report.docx`, `archive/Q3_first_run_random_split.docx`).
This page lists every change made to their text so they can confirm it.

## Question 1 (written by GitHub user Tran203)
| # | Change | Why |
|---|---|---|
| 1 | "Misuse: false reassurance" row: *"…almost identical to 'repeat last year's outcome' (they differ for one municipality, Q5.3)"* now reads *"…identical to 'repeat last year's outcome' (Q5.3)"* | On the 2023 test year the locked model and the rule agree on all 240 municipalities. The one-municipality difference is between the champion and the MLP (McNemar, Q6.2). |
| 2 | "The audit outcome matter for residents" → "matters" | Typo |
| 3 | Added in-text citations; references moved into one combined list (Treasury items labelled n.d.-a, n.d.-b, n.d.-c) | One reference list for the whole report |
| 4 | Table 1.3 "Limitations" rows condensed into one row; wording otherwise kept | Length |

## Question 2 (written by Thapelo)
| # | Change | Why |
|---|---|---|
| 1 | **§2.4.4: the decision on `prior_audit_outcome` now says it is *included*** (it said *excluded*, with a switch `USE_PRIOR_AUDIT_OUTCOME = False`). Pipeline table steps 1 and 3 updated to match. | The final model, the saved pipeline, the app and every result in Q3–Q8 include it. No script in the repository has that switch, so the original text contradicted the rest of the report. If the team prefers a ratios-only model, ablation A1 (Q6.1) is exactly that model (validation macro-F1 0.692 against 0.887). |
| 2 | "Four possible sources" → "Five" (in the audit table) | The text lists five |
| 3 | Table 2.3: "approximate at-risk share read from Figure 5" replaced by exact counts: 447/950 (47.1%), 103/244 (42.2%), 103/240 (42.9%) | Exact values are available from `modeling_dataset.csv` |
| 4 | Zeros-versus-missing: "to be confirmed" → confirmed (debtor cube starts 2020, repairs 2019, grants 2020 with 182 municipalities) | Checked in the raw extracts; recoding to missing is left as a recommended improvement |
| 5 | "capping or robust scaling is tested in the ablation study" → "robust scaling was tested in Q5.1" | Robust scaling is one of the Optuna search options; the ablations test other components |
| 6 | The separate feature-engineering table was merged into the data dictionary (Table 2.1, calculations kept); the execution-order table moved to Appendix E and now covers all 11 steps | Length; the pipeline now extends beyond Q2 |
| 7 | Interpretations of Figures 1–5 condensed | Length. **All numbers were checked against the data and are correct** (outlier counts, surplus and debtor-day quartiles, at-risk share by year). |

**Warning for Thapelo:** the Word document refers to a version of `pipeline_q24.py` with a `USE_PRIOR_AUDIT_OUTCOME` flag. That version is not in the repository. Please do not push a version of the script with the feature switched off:
`models/final_pipeline.joblib`, `src/models.py` and the dashboard all assume `prior_audit_outcome` is an input.

## Question 3 (rewritten)
The first Question 3 (Pamela) used a random 70/15/15 split and the year column, and reported the test set before tuning.
Question 3 was re-run on the time-based split of Q2.3 and written again from the new results. The original is archived
(`notebooks/archive/`, `reports/archive/`). **The second neural architecture (a residual tabular network) must be approved by the
lecturer** (the brief allows "an approved tabular neural network"); the concept note had planned a GRU. Please confirm the approval.

## Questions 4–8
Written from the result files (`results/`), condensed from `IDA117V_Q4-Q8_Report_Sections.docx`; full per-model tables, curves,
fairness detail and dashboard screenshots are in Appendices A–D.
