// Questions 1 and 2. Text by the team members who wrote them (Q1: GitHub user Tran203; Q2: Thapelo),
// lightly condensed for length. Changes of substance are listed in docs/report_merge_notes.md.
const L = require("./lib");
const { P, H1, H2, H3, B, table, figure, sideFigure, caption, f3, pct, spacer } = L;

module.exports = function q1q2(ctx) {
  const c = [];
  const add = (...xs) => xs.flat().forEach((x) => c.push(x));

  // ======================================================== QUESTION 1
  add(
    H1("Question 1: Problem definition, success measures and data justification"),
    H2("1.1 Service-delivery problem and classification task"),
    P("Every year the Auditor-General of South Africa (AGSA) audits all 257 municipalities (AGSA, n.d.). Some pass and many fail, for various reasons or because they do not submit their financial statements. The audit outcome matters for residents because poor financial management leads to unpaid municipal bills, neglected infrastructure and failing services. The problem is that audit results arrive long after the financial year has ended, so Treasury usually responds only once the damage has been done."),
    P("**Affected population.** Residents of poorly governed municipalities, who bear the service failures, and the creditors and suppliers who go unpaid. **Decision-maker.** National Treasury's local government support function and the provincial treasuries, who decide each year where to send financial-management support, secondments and oversight. **Intended benefit.** Earlier, evidence-based and more consistent targeting of limited support, so that struggling municipalities are reached before service delivery collapses. The model supports human judgement; it does not replace the audit or decide funding."),
    table(["Element", "Definition"], [
      ["Unit of prediction", "One municipality in one financial year t (a municipality-year), identified by its Municipal Demarcation Board code."],
      ["Inputs", "Nine financial indicators for year t (total revenue, total expenditure, operating surplus, cash coverage, collection rate, debtor days, repairs and maintenance ratio, irregular expenditure ratio, grant dependency) plus the audit outcome for year t (at_risk or not_at_risk)."],
      ["Target classes", "The AGSA outcome for year t+1. **at_risk** = qualified, adverse, disclaimer or outstanding. **not_at_risk** = unqualified, with or without findings."],
      ["Prediction horizon", "One audit cycle: the flag can be issued as soon as the year t results are known, about a year before the year t+1 outcome is published."],
      ["Intended decision", "Rank municipalities by risk so that Treasury can prioritise its limited support budget and staff."],
    ], [2000, 7752]),
    caption("Table 1.1: The classification task."),

    H2("1.2 Success measures and the cost of errors"),
    P("**Primary technical metric: macro-F1**, the average of the at_risk and not_at_risk F1 scores, so both classes count equally. It is used instead of accuracy because the classes are unevenly sized (about 55/45): a model that always predicts not_at_risk reaches 57.8% accuracy on the 2022 validation year but a macro-F1 of only 0.366. Recall, precision, ROC-AUC and PR-AUC for the at_risk class are reported alongside it."),
    P("**Service-delivery success indicators.** _Coverage_: the share of municipalities that go on to receive a poor audit that had been flagged one cycle earlier (recall for at_risk), i.e. the proportion of failing municipalities Treasury could have reached before the failure. _Targeting efficiency_: the share of flagged municipalities that do receive a poor audit (precision for at_risk), which shows how much of Treasury's scarce support capacity goes to municipalities in genuine need. Whether the support that follows improves services can only be judged in later audit cycles and is outside the scope of this project."),
    table(["Error", "What happens", "Cost"], [
      ["False negative", "A municipality that will fail is not flagged.", "Support arrives late or not at all. Unpaid creditors, service breakdowns and irregular spending continue for another year, and residents bear the cost."],
      ["False positive", "A municipality that will pass is flagged.", "An unnecessary visit or secondment uses scarce Treasury capacity that another municipality needed, and the flag may be read as a verdict."],
    ], [1500, 3000, 5252]),
    caption("Table 1.2: Cost of the two error types."),
    P("A false negative is the more costly error: a flag is only a request to look closer and offer support, which is cheap and reversible, whereas a missed failure is not, so recall matters most. Support capacity is limited, however, so precision cannot be ignored. This is why a balanced metric (macro-F1) is the primary measure and both indicators are monitored."),

    H2("1.3 Dataset justification, risks and safeguards"),
    P("The data is _Municipal Money, Municipal Finance Data_, published by National Treasury (National Treasury, n.d.-a)."),
    table(["Aspect", "Entry"], [
      ["Relevance", "An official, municipality-level source of audited financial statements and AGSA audit opinions. The target is published directly, so no hand-labelling is needed, and the indicators are the kind Treasury and AGSA use to judge financial health. No personal data is needed."],
      ["Provenance", "Owner: National Treasury (platform run with OpenUp). Financial data are MFMA section 71 submissions signed off by each municipal manager and CFO (\"audited actual\" amounts; Republic of South Africa, 2003); audit opinions come from AGSA reports. The extracts were downloaded through the public API and are committed to the repository (data/raw)."],
      ["Licence", "Terms of Use (National Treasury, n.d.-c): use for commercial and non-commercial purposes at no cost, including copying, publishing and distributing. Conditions: acknowledge National Treasury and the date of publication; do not mislead; do not imply Treasury endorses our analysis; do not use personal data. No warranty of accuracy. The extracts may therefore be redistributed in the repository with attribution."],
      ["Coverage", "257 municipalities today (292 including disestablished ones). Audit opinions 2011–2024; financial datasets 2018–2025 (debtors from 2020, repairs and maintenance from 2019, grants from 2020 for 182 municipalities). Modelling set: 1,434 labelled municipality-years (feature years 2018–2023, target years 2019–2024), 54.5% not_at_risk and 45.5% at_risk, plus 245 rows for 2024 used to forecast the 2025 audit."],
      ["Limitations", "(1) Figures are only as reliable as each municipality's submission; some are implausible (e.g. cash coverage of −23.7 months) and are kept as reported. (2) Missing items are recorded as 0 (debtor days before 2020, repairs and maintenance before 2019). (3) The grants extract appears truncated (100,000 rows, 182 municipalities). (4) The 2019-20 chart-of-accounts change (mSCOA) and boundary changes alter line items over time. (5) Municipalities that do not submit statements are the highest-risk group but have the least data. (6) Only six feature years are available, so the sample is small."],
    ], [1500, 8252]),
    caption("Table 1.3: Dataset card summary (full card: docs/dataset_card.md)."),
    P("The table below lists the POPIA, privacy, fairness and misuse risks that apply and the proposed safeguards (Republic of South Africa, 2013)."),
    table(["Risk", "Why it matters here", "Safeguard"], [
      ["POPIA and privacy", "POPIA protects personal information. The Municipal Officials dataset lists named staff with emails and phone numbers. Municipal finances are public records but describe identifiable public bodies.", "Officials and all contact fields were excluded at download; the nine raw extracts contain no staff names, emails or phone numbers; no linking to other sources; the app needs no credentials and stores nothing; uploads are limited to 500 rows of the financial columns."],
      ["Fairness", "Province and municipality type are proxies for rurality and poverty, and audit history carries past failure forward, so some groups may be flagged wrongly more often.", "Province and type are not model inputs. Recall and false-positive rate are reported by province and type (Q8.1 found, for example, a 28.6% false-alarm rate in the Northern Cape and 70.0% recall in Limpopo). Flagged lists are reviewed by province before support is allocated."],
      ["Misuse: punishment", "A flag could be used to cut funding, publish league tables or judge officials.", "Decision support only: a flag means \"look closer and offer support\". No automatic allocation of funds. The app carries a responsible-use notice and a list of when not to use the model."],
      ["Misuse: false reassurance", "On the 2023 test year the model's yes/no predictions are identical to \"repeat last year's outcome\" (Q5.3), so it adds little for a municipality that deteriorates after a clean audit.", "State this limitation wherever results are shown; do not treat \"not at risk\" as safe; re-check the model against the published AGSA outcomes every year."],
      ["Misuse: gaming and reuse", "Once the indicators are known to matter, reported figures could be adjusted, and others (e.g. lenders) could reuse the scores for credit decisions.", "Access limited to Treasury support staff; documented purpose and limitations; scores not published as rankings; re-validation after accounting or boundary changes."],
    ], [1500, 3900, 4352]),
    caption("Table 1.4: Risks and safeguards."),
  );

  // ======================================================== QUESTION 2
  add(
    H1("Question 2: Data audit, visualisation, splitting and preparation pipeline"),
    P("The analysis file (modeling_dataset.csv) holds 1,434 municipality-year records. Each record describes one municipality in financial year t (2018 to 2023) through financial indicators built from Municipal Money (audited actual figures) and carries the AGSA result for year t+1 (2019 to 2024) as the target. This follows the concept note: the flag is issued once the year t results are known, one audit cycle before the year t+1 outcome is published."),
    H2("2.1 Data dictionary and data audit"),
    table(["Column", "Role", "Unit", "Meaning and source", "Null %"], [
      ["demarcation.code", "Identifier", "text", "Municipal Demarcation Board code (e.g. BUF); join key across all Treasury cubes and the audit file", "0"],
      ["financial_year_end.year", "Identifier (time)", "year", "Financial year t; orders and splits the records, not a model input", "0"],
      ["Name", "Reference", "text", "Municipality name; reporting only", "0"],
      ["total_revenue", "Feature", "rand", "Sum of income lines (mSCOA item codes below 2900), Income and Expenditure cube, audited actual", "0"],
      ["total_expenditure", "Feature", "rand", "Sum of expenditure lines (item codes 3000 to 4399), same cube", "0"],
      ["operating_surplus", "Feature", "rand", "total_revenue minus total_expenditure (negative = deficit)", "0"],
      ["cash_coverage_ratio", "Feature", "months", "Cash and equivalents (Financial Position cube) ÷ (total_expenditure ÷ 12)", "0.1"],
      ["collection_rate", "Feature", "proportion", "(Property rates + service charges − debt impairment) ÷ (property rates + service charges)", "8.4"],
      ["debtor_days", "Feature", "days", "Total owed by customers (Aged Debtor cube) ÷ (total_revenue ÷ 365)", "0"],
      ["repairs_maintenance_ratio", "Feature", "proportion", "Repairs and maintenance spending (Repairs and Maintenance cube) ÷ total_expenditure", "0.1"],
      ["irregular_expenditure_ratio", "Feature", "proportion", "Irregular expenditure (Unauthorised, Irregular, Fruitless and Wasteful Expenditure cube) ÷ total_expenditure", "0.1"],
      ["grant_dependency", "Feature", "proportion", "All grants received (Grants cube) ÷ total_revenue", "0"],
      ["prior_audit_outcome", "Feature", "category", "Year t AGSA result grouped as not_at_risk / at_risk; past information, not leakage (2.4.4)", "0"],
      ["prior_audit_opinion_raw", "Reference", "category", "Original AGSA opinion for year t; traceability only", "0"],
      ["target_next_year", "Target", "category", "AGSA risk class for year t+1; encoded 0/1 in the pipeline", "0"],
      ["target_opinion_raw", "Reference", "category", "Original AGSA opinion for year t+1; never a model input", "0"],
    ], [2250, 1150, 850, 5000, 502], { size: 16 }),
    caption("Table 2.1: Data dictionary (docs/data_dictionary.md and reports/data_dictionary.csv). Identifier and reference columns are never given to a model."),
    P("The audit (script audit_q21_v2.py, output audit_report.txt) covered all 1,434 records:", { spacing: { after: 60 } }),
    table(["Check", "Finding", "Action taken"], [
      ["Class balance", "781 Not at risk (54.5%) and 653 At risk (45.5%): only mildly imbalanced.", "No resampling; class weights at training time (2.4.2)."],
      ["Duplicates", "0 duplicate municipality-year keys and 0 fully duplicate rows.", "None needed."],
      ["Missing values", "Average 0.9% across features. collection_rate 8.4% (undefined when billed revenue is zero); cash_coverage_ratio, repairs_maintenance_ratio and irregular_expenditure_ratio 0.1% each; all others complete.", "Median imputation, learned on training data only (2.4.2)."],
      ["Invalid or implausible values", "No column is entirely zero. 18 records have negative total_revenue and 11 negative total_expenditure, which is not economically plausible and is treated as a likely reporting or aggregation error. Other negatives can be valid: operating_surplus 1,032 records (a deficit), cash_coverage_ratio 167 (negative cash balance).", "Retained and flagged for checking against the source; robust scaling was tested in Q5.1."],
      ["Zeros that may mean \"no data\"", "For Buffalo City, debtor_days is 0 in 2018–2020, grant_dependency is 0 in 2018–2019 and collection_rate is exactly 1 in 2018–2021. The extracts confirm that the debtor cube starts in 2020, repairs in 2019 and grants in 2020 (182 municipalities), so earlier zeros are absent data recorded as 0.", "Kept as reported and disclosed as a limitation (2.5); recoding to missing with an indicator is a recommended improvement."],
      ["Outliers", "Outside 3 × IQR: total_revenue 94, total_expenditure 96, operating_surplus 111, cash_coverage_ratio 59, collection_rate 136, debtor_days 40, repairs_maintenance_ratio 32, irregular_expenditure_ratio 90, grant_dependency 6. The revenue and expenditure outliers most likely reflect the large metropolitan municipalities, which are genuinely larger.", "Not deleted (they are real municipalities); capped for plotting only."],
      ["Leakage", "Five possible sources examined; none found (below).", "Design rules in 2.1 and 2.4.3."],
    ], [1550, 5400, 2802]),
    caption("Table 2.2: Data audit."),
    P("**Possible leakage.** Leakage means the model sees at training time something that would not exist at prediction time. Five sources were checked. (1) _Target-year information in the inputs_: all inputs describe year t and the target is the AGSA result for year t+1. (2) _Audited figures_: audited actual figures for year t are safe, because the year t audit is finished and public before year t+1 is predicted; they would be leakage only if the target were year t's own opinion. The irregular-expenditure figures are audit-derived and used under the same rule. (3) _Identifiers and answer-like columns_: municipality code, name, year and the raw opinion of year t+1 are excluded. (4) _Last year's outcome_: prior_audit_outcome is past information and so not leakage, but it is a strong \"repeat last year\" signal and is treated as an explicit team decision (2.4.4). (5) _Preprocessing leakage_: medians, scaling factors and category lists are learned from training data only."),

    H2("2.2 Visualisations"),
    P("Five figures were produced from the analysis file (script visualize_q22_v2.py, n = 1,434): the target distribution, missingness, two feature–target relationships and one temporal view."),
    sideFigure("reports/figures/01_target_distribution.png", "Figure 1: Distribution of the target (audit risk at year t+1). Units: number of municipality-year records.", [
      "**Interpretation.** 781 records are Not at risk and 653 At risk (about 54.5% and 45.5%). The classes are close to balanced, so accuracy is not dominated by one class, but macro-F1 is still reported because missing an at-risk municipality (a false negative) costs more than flagging a healthy one."], 330, 3950),
    sideFigure("reports/figures/02_missingness_by_feature.png", "Figure 2: Missing values by feature. Units: % of the 1,434 records.", [
      "**Interpretation.** collection_rate is the only feature with notable missingness (about 8.4%); it is undefined when billed revenue is zero. Three other features are about 0.1% missing and the rest are complete, so median imputation is adequate. The chart cannot show the zero-versus-missing issue in Table 2.2, because zeros count as present values."], 360, 4150),
    sideFigure("reports/figures/03_surplus_vs_risk.png", "Figure 3: Year t operating surplus vs year t+1 audit risk. Units: rand, capped at the 5th and 95th percentile for display only; the axis is ×10⁸.", [
      "**Interpretation.** Most municipalities run an operating deficit in both groups, partly because revenue here excludes capital transfers while expenditure includes non-cash items such as depreciation. Municipalities at risk a year later had a lower median surplus (about −R45.8 million against −R13.4 million) and a longer lower tail (middle half from about −R171 million to −R11 million, against −R67 million to +R10 million). Weaker finances in year t go with worse audit outcomes in year t+1, but the boxes overlap heavily, so surplus alone separates the groups only weakly."], 340, 4050),
    sideFigure("reports/figures/04_debtordays_vs_risk.png", "Figure 4: Year t debtor days vs year t+1 audit risk. Units: days of revenue owed, capped at the 95th percentile.", [
      "**Interpretation.** At-risk municipalities have a much higher upper quartile (about 718 days) than not-at-risk municipalities (about 243 days, median 62). Municipalities that struggle to collect what they bill are more likely to fail the next audit, which makes debtor days a promising feature. Caution: the lower end of both boxes is zero, and many of these zeros are missing data in the early years (Table 2.2), which compresses the lower quartile."], 340, 4050),
    sideFigure("reports/figures/05_risk_trend_by_year.png", "Figure 5: Share of at-risk outcomes by feature year (observed outcomes, not predictions). Units: % of that year's records.", [
      "**Interpretation.** The at-risk share fell from about 55% (t = 2018) to about 48% (2019) and then levelled at roughly 42–43% from 2020 to 2023. The base rate is therefore not constant: municipalities were somewhat less likely to be at risk in later years. This matters for the split in 2.3, because a model trained on the earlier, higher-risk years meets a lower base rate in validation and test. Records per year are stable (231 to 244), so the trend is not an artefact of sample size."], 360, 4150),

    H2("2.3 Train, validation and test split"),
    P("Records are split by feature year t in time order: the oldest years train the model, the next year validates it and the most recent year tests it. The split is made before any transformation is learned (script split_q23_v2.py)."),
    table(["Split", "Feature years (t)", "Outcome years (t+1)", "Records", "At risk"], [
      ["Training", "2018–2021", "2019–2022", "950", "447 (47.1%)"],
      ["Validation", "2022", "2023", "244", "103 (42.2%)"],
      ["Test", "2023", "2024", "240", "103 (42.9%)"],
    ], [1800, 2000, 2300, 1400, 2252]),
    caption("Table 2.3: Time-based split (exact class counts from modeling_dataset.csv)."),
    B("**It mirrors deployment.** In real use Treasury issues a flag using only years already finished; training on the past and testing on the most recent year reproduces that and avoids look-ahead bias."),
    B("**The test set is reserved.** It is used once, for the final locked model (Q5.3). Model selection and tuning use the validation year, or walk-forward cross-validation inside the training years only."),
    B("**Stratification and groups.** Time order takes priority over stratified sampling, so the class balance of each split is reported instead (all close to balanced). The same municipality appears in several years, so training and test contain the same municipalities in different years; this is realistic but means some performance reflects municipality history (a recorded limitation)."),
    B("**Alternatives rejected.** A random stratified split (later years would train a model tested on earlier years, optimistic results) and grouped k-fold by municipality (ignores time order). **Walk-forward cross-validation** is used for tuning inside the training years (Q5): train on 2018, validate on 2019; train on 2018–2019, validate on 2020; and so on."),
    B("**Limitation.** Validation and test each contain about 240 records from a single year, so single-year estimates are noisy; Q4 therefore reports cross-validation means and Q8 bootstrap confidence intervals."),

    H2("2.4 Preparation pipeline"),
    P("**Feature engineering.** The raw Treasury tables list one row per line item. They were aggregated into nine municipality-year indicators from the audited actual figures of year t (Table 2.1; script build_modeling_dataset.py, which downloads the data through the Municipal Money API). Totals were built by summing the individual line items rather than reading Treasury's own subtotal rows (codes 2900 and 4400), which were only present for 2023 onward; summing the components recovered 2018–2022 and raised the usable records from 240 to 1,434. The subtotal rows are excluded so that nothing is counted twice."),
    P("All steps are inside one scikit-learn ColumnTransformer (script pipeline_q24.py; Pedregosa et al., 2011), so the same preparation is applied identically in training, evaluation and the user interface:", { spacing: { after: 60 } }),
    table(["Step", "What is done", "Why"], [
      ["1. Select inputs", "The nine numeric features and prior_audit_outcome. Identifiers, names, year and raw opinion text are dropped. Target mapped not_at_risk = 0, at_risk = 1.", "Keeps answer-like and identifying columns out of the model."],
      ["2. Imputation", "Median for numeric features; most frequent value for the categorical feature.", "The median is robust to the extreme values in Table 2.2; learned from training data only."],
      ["3. Encoding", "One-hot encoding of prior_audit_outcome; unseen categories ignored.", "Models need numbers; unseen categories must not crash the interface."],
      ["4. Scaling", "StandardScaler (mean 0, SD 1), learned on training data. Robust scaling was tested as a hyper-parameter in Q5.1.", "Needed by logistic regression and neural networks so that rand-sized features do not swamp ratios."],
      ["5. Class imbalance", "No resampling. Class weights (class_weight = balanced, or weighted loss for the neural networks).", "The imbalance is mild (about 55/45), so weighting is simpler and avoids creating synthetic municipalities."],
      ["6. Persistence", "The fitted pipeline is saved (preprocessor.joblib; the final model is saved with it as final_pipeline.joblib).", "Every model and the interface in Q7 use the identical preparation."],
    ], [1500, 4600, 3652]),
    caption("Table 2.4: Preparation pipeline."),
    P("**How leakage is prevented.** The pipeline is fitted on the training split only; validation and test are only transformed, using the training medians, scales and categories. Tuning uses the validation year or cross-validation inside the training years, and the test year is touched once, at the end. Inputs come only from year t and the target from year t+1. Records are split before any statistic is calculated, and the split is by time, never random."),
    P("**2.4.4 Decision on prior_audit_outcome.** Using the year t audit result as an input is not leakage, because it is known before year t+1 is predicted, and the concept note allows \"audit outcome history up to t\". It is, however, a strong \"repeat last year\" signal. The final model **includes** it, because Treasury's decision can legitimately use it and because leaving it out would hide the persistence effect rather than remove it. Its influence is made visible in three ways: the \"repeat last year's outcome\" baseline in Q3.1 and Q4.1, the ablation that removes it in Q6.1 (validation macro-F1 falls from 0.887 to 0.692, so a financial-ratios-only model is clearly weaker), and the discussion of limitations in Q8.1."),
    P("**2.5 Limitations carried forward.** (1) Zeros versus missing data (Table 2.2). (2) The revenue (below 2900) and expenditure (3000 to 4399) item-code ranges follow the mSCOA layout in Treasury's published table and should be cross-checked against its chart-of-accounts documentation. (3) Validation and test sets of about 240 records from one year are noisy. (4) The at-risk share fell over time (Figure 5) and the same municipalities appear in training and test."),
  );
  return c;
};
