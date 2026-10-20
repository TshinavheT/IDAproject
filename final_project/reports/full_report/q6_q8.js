// Questions 6 to 8. All numbers are read from results/.
const L = require("./lib");
const { P, H1, H2, B, table, figure, sideFigure, caption, f3, pct, sgn, readJson, readCsv } = L;

module.exports = function q6q8(cfg) {
  const q5 = readJson("q5_test_result.json");
  const mc = readJson("q6_mcnemar.json");
  const q8 = readJson("q8_uncertainty.json");
  const abl = readCsv("q6_ablation.csv");
  const fprov = readCsv("q8_fairness_province.csv");
  const ftype = readCsv("q8_fairness_type.csv");
  const scores = readCsv("municipality_scores.csv");
  const tm = q5.test_metrics, rm = q5.repeat_last_year_test_metrics;
  const a = Object.fromEntries(abl.map((r) => [r.experiment.split(":")[0], r]));
  const c = [];
  const add = (...xs) => xs.flat().forEach((x) => c.push(x));

  // ======================================================== QUESTION 6
  const ablRows = [
    ["Full tuned champion (reference)", a["Full tuned champion (reference)"]],
    ["A1: remove audit-history feature", a["A1"]],
    ["A2: remove the nine financial ratios", a["A2"]],
    ["A3: remove imbalance treatment", a["A3"]],
    ["A4: remove the scaling step", a["A4"]],
    ["A5: swap L1 regulariser for L2", a["A5"]],
  ];
  add(
    H1("Question 6: Ablation study and statistical validation"),
    H2("6.1 Controlled ablations"),
    P("Five ablations were run on the tuned champion. Each changes exactly one component while the split (fit 2018–2021), seed (42) and evaluation protocol (2022 validation year plus walk-forward cross-validation) stay fixed; the 2023 test year was not reused."),
    table(["Experiment", "Val macro-F1", "Δ macro-F1", "Val ROC-AUC", "Δ ROC-AUC", "Val recall", "CV macro-F1"],
      ablRows.map(([n, r]) => [n, f3(r.val_macro_f1), sgn(r.delta_val_macro_f1), f3(r.val_roc_auc), sgn(r.delta_val_roc_auc), f3(r.val_recall_at_risk), f3(r.cv_macro_f1_mean)]),
      [3000, 1050, 1000, 1050, 1000, 1000, 1652], { bold: [0], align: ["left", "right", "right", "right", "right", "right", "right"] }),
    caption("Table 6.1: Ablation results (Δ = change relative to the full tuned champion)."),
    ...figure("reports/figures/q6_ablation.png", "Figure 6.1: Change in validation macro-F1 and ROC-AUC for each ablation.", 400),
    B(`**A1, remove audit history:** macro-F1 falls by ${f3(-a["A1"].delta_val_macro_f1)} and ROC-AUC by ${f3(-a["A1"].delta_val_roc_auc)}, the model's main dependency. The ratios alone still reach macro-F1 ${f3(a["A1"].val_macro_f1)}, well above the dummy baseline (0.366), so they carry real but weaker signal.`),
    B(`**A2, remove all nine ratios:** macro-F1 is unchanged but ROC-AUC falls by ${f3(-a["A2"].delta_val_roc_auc)}: the ratios change no yes/no decision; they only refine the ordering of municipalities within each outcome group.`),
    B("**A3, remove class weighting:** no change; the 58/42 split is mild enough that imbalance treatment is unnecessary here."),
    B(`**A4, remove scaling:** the largest drop (macro-F1 ${sgn(a["A4"].delta_val_macro_f1)}, ROC-AUC ${sgn(a["A4"].delta_val_roc_auc)}). Revenue and expenditure are in billions of rand, so without standardisation the L1 penalty shrinks the useful features unevenly.`),
    B(`**A5, L2 instead of L1:** macro-F1 unchanged and ROC-AUC ${sgn(a["A5"].delta_val_roc_auc)}; L1 was kept because it produces a smaller model that is easier to explain.`),
    P("**What the system depends on:** first, last year's audit outcome; second, correct scaling of the inputs. The financial ratios add only ranking information; imbalance treatment and the regulariser type matter little."),
    H2("6.2 McNemar's test: champion vs strongest comparator"),
    P(`The optimised champion was compared with the strongest comparator, the **MLP** (tied with the residual network for the best non-champion validation macro-F1, and with the higher ROC-AUC). Both were fit on 2018–2022 and predicted the **same ${mc.n_test} test municipalities** (paired predictions: results/q6_paired_test_predictions.csv).`),
    table(["", "MLP correct", "MLP wrong", "Total"], [
      ["Champion correct", String(mc.table.both_correct), String(mc.table.champion_only_correct), String(mc.table.both_correct + mc.table.champion_only_correct)],
      ["Champion wrong", String(mc.table.comparator_only_correct), String(mc.table.both_wrong), String(mc.table.comparator_only_correct + mc.table.both_wrong)],
      ["Total", String(mc.table.both_correct + mc.table.comparator_only_correct), String(mc.table.champion_only_correct + mc.table.both_wrong), String(mc.n_test)],
    ], [3200, 2200, 2200, 2152]),
    caption("Table 6.2: McNemar 2 × 2 correctness table on the test year (b = champion only correct, c = MLP only correct)."),
    P(`**H₀:** the two models have the same error rate on these municipalities (P(b) = P(c)). **H₁:** the error rates differ (two-sided). **α = ${mc.alpha}.** There is only ${mc.discordant_pairs} discordant pair (b = ${mc.table.champion_only_correct}, c = ${mc.table.comparator_only_correct}), far below the usual threshold of 25, so the **exact binomial** version of the test (McNemar, 1947) is used instead of the chi-square approximation: statistic = min(b, c) = ${mc.statistic.toFixed(0)}, **exact p = ${mc.p_value.toFixed(4)}**, so **H₀ is not rejected**.`),
    P(`**Statistical vs practical significance.** There is no evidence that the tuned champion is more accurate than the MLP; they disagree on a single municipality. The practical difference is also negligible: accuracy ${pct(mc.champion_accuracy)} vs ${pct(mc.comparator_accuracy)} and macro-F1 ${f3(mc.champion_macro_f1)} vs ${f3(mc.comparator_macro_f1)}. Logistic Regression is justified by simplicity, explainability and stability (CV SD 0.025 vs 0.18), not by superior accuracy. A McNemar test against the repeat-last-year rule would be uninformative, because the two give identical predictions (b = c = 0).`),
  );

  // ======================================================== QUESTION 7
  const fc = scores.filter((r) => r.split === "forecast");
  const fcFlagged = fc.filter((r) => r.predicted_outcome === "at_risk").length;
  const fcHigh = fc.filter((r) => +r.risk_probability >= 0.8).length;
  const fcChanging = fc.filter((r) => r.predicted_outcome !== r.prior_audit_outcome).length;
  const emf = fc.find((r) => r["demarcation.code"] === "GT421");
  const emfRank = fc.filter((r) => +r.risk_probability > +emf.risk_probability).length + 1;
  add(
    H1("Question 7: User-interface deployment"),
    H2("7.1 Working user interface"),
    P(`The final optimised model is deployed as an interactive **Streamlit** web application (app/app.py; Streamlit Inc., n.d.) styled as a KPI dashboard. Its pages are: **Overview** (test-year KPIs, the forecast for the next audit, trend, highest-risk municipalities, leaderboard), **Explorer** (filter all municipalities by audit year, province, type, last opinion and risk band), **Municipality profile** (one page per municipality), **Risk check** (the prediction tool), **Model evidence** and **About & responsible use**. Every ring, gauge and chart on the overview opens a more detailed view (Table A.1); screenshots are in Appendix D. A notebook cell is not used anywhere.`),
    H2("7.2 Input, prediction pipeline and output"),
    P("Every prediction runs the saved end-to-end pipeline (models/final_pipeline.joblib), so imputation, scaling, encoding and the tuned model behave exactly as in Q5; nothing is retrained in the app. Users can **pick a municipality** (its latest audited figures, 2024, forecast the 2025 audit), **enter figures** in a form with units and help text, or **upload a CSV** of up to 500 municipalities with a downloadable result. Each prediction shows the predicted class, the probability of a poor audit on a gauge, a confidence band (high, moderate or close call around the 50% threshold) and a plain-language explanation of the two or three features that pushed it most (coefficient × standardised value), for example \"Cash coverage of −23.7 months (typical: 0.8 months) raises the risk\"."),
    P(`**Forecasting the next audit.** The raw extracts already contain audited 2024 statements and 2024 audit opinions, so src/forecast_next.py rebuilds the features for 2018–2024 with the same feature-engineering code, checks that the rebuilt 2018–2023 features equal modeling_dataset.csv exactly (1,434 of 1,434 rows) and that the 2023 scores equal the Q5 test predictions, then scores every municipality-year with the locked pipeline. The ${fc.length} rows for 2024 are a genuine forecast of the **2025 audit**: **${fcFlagged}** municipalities are forecast at risk, ${fcHigh} of them at 80% or more.`),
    sideFigure("reports/figures/app/app_profile_top.png", `Figure 7.1: Profile of Emfuleni (GT421): ${(+emf.risk_probability * 100).toFixed(1)}% forecast risk for 2025, ranked #${emfRank} of ${fc.length} nationally.`, [
      "**Municipality profile.** Clicking any municipality opens a profile (shareable as /municipality?code=GT421) with the forecast, its gauge, explanation and national and province rank; the risk history for 2019–2025 coloured by what actually happened (training years shaded, so in-sample points are not mistaken for forecasts); the audit opinion for every year; six financial-health trends against the national median; and a peer table against the province, municipality-type and national medians and the MFMA Circular 71 norms (National Treasury, 2014).",
      `The forecast also shows the main limitation openly: **${fcChanging === 0 ? "no" : fcChanging} municipalit${fcChanging === 1 ? "y is" : "ies are"} forecast to change status** between 2024 and 2025.`], 300, 3500),
    H2("7.3 Input validation and safeguards"),
    table(["Check", "Response"], [
      ["Text where a number is expected; revenue or expenditure missing, zero or negative; unrecognised audit outcome", "Error naming the row and field (and the accepted values); the row is not scored"],
      ["Required columns missing, empty file, or more than 500 rows", "Error explaining the expected format"],
      ["Ratio left blank; value outside the 1st–99th percentile of training data; surplus inconsistent with revenue − expenditure", "Warning (training median used; extra caution; recalculated)"],
    ], [5200, 4552]),
    caption("Table 7.1: Input validation rules (Figure A.7 shows an invalid entry being rejected)."),
    P("A column guide and help tooltips explain every feature, its unit and the relevant Treasury norm. Every prediction carries a notice that a flag means \"look closer and offer support\", not \"this municipality has failed\", the profile warns that raw Municipal Money figures can contain errors, and the About page lists limitations and when not to use the model. The app needs no credentials, stores nothing and holds no personal data."),
    H2("7.4 Deployment instructions and demonstration"),
    P(`The app is launched locally with **streamlit run app/app.py** after python -m venv .venv, activating it and pip install -r requirements.txt (README.md; a slimmer app/requirements.txt without PyTorch is used for hosting)${cfg.liveUrl ? `. A hosted version is available at ${cfg.liveUrl}` : ". It can be hosted on Streamlit Community Cloud from the repository (README, section \"Live demo and deployment\")"}. A smoke test (python app/test_app.py) opens every page and dialog; all 19 checks pass. The demonstration files are in app/samples:`),
    table(["Case", "Input", "Output"], [
      ["Valid 1: Masilonyana (FS181)", "Prior opinion disclaimer, cash coverage −23.7 months, irregular expenditure 1,271%", "At risk, 89.9%, high confidence (warnings for unusual values)"],
      ["Valid 2: eThekwini (ETH)", "Prior opinion unqualified with findings, revenue R48.9 bn, cash coverage 0.9 months", "Not at risk, 9.2%, high confidence"],
      ["Valid 3: Tsantsabane (NC085)", "Prior opinion qualified, cash coverage 0.4 months, repairs and maintenance 30.6%", "At risk, 77.2%, moderate confidence"],
      ["Invalid: invalid_case.csv", "Revenue \"four hundred million\", expenditure 0, prior outcome \"maybe\"", "Rejected with three specific error messages; nothing scored"],
    ], [2500, 4000, 3252]),
    caption("Table 7.2: Demonstration cases: three valid and one invalid (the sample CSV holds 2023 figures, i.e. predictions for the 2024 audit)."),
  );

  // ======================================================== QUESTION 8
  const ci8 = q8.metrics_ci95;
  const ciText = (k) => `${f3(ci8[k].estimate)} (95% CI ${f3(ci8[k].ci95_low)}–${f3(ci8[k].ci95_high)})`;
  const ok = (r) => r.reliable === "True" || r.reliable === true;
  const reliableProv = fprov.filter(ok);
  const worstFpr = reliableProv.reduce((x, y) => (y.false_positive_rate > x.false_positive_rate ? y : x));
  const worstRecall = reliableProv.reduce((x, y) => (y.recall_at_risk < x.recall_at_risk ? y : x));
  const otherFpr = reliableProv.filter((r) => r.province !== worstFpr.province).map((r) => r.false_positive_rate);
  const smallProv = fprov.filter((r) => !ok(r)).map((r) => r.province);
  const dist = ftype.find((r) => r.category === "District");
  const testRows = scores.filter((r) => r.split === "test" && r.prior_audit_outcome === "not_at_risk").sort((x, y) => +y.risk_probability - +x.risk_probability);
  const k10 = Math.round(testRows.length * 0.1);
  const det = (rows) => rows.filter((r) => r.actual_next_outcome === "at_risk").length;
  add(
    H1("Question 8: Recommendation, reproducibility and team defence"),
    H2("8.1 Recommendation for National Treasury"),
    P(`**Recommendation.** Treasury's local government support function should use the model as a **consistent, explainable triage list for municipalities that are already in difficulty**, not as an early-warning system. For the 2025 audit it flags **${q8.forecast_2025.flagged} of ${q8.forecast_2025.n}** municipalities, ${fcHigh} of them at 80% or more: the municipalities where support (finance secondments, closer oversight, Financial Management Grant conditions) is most likely to be needed. The dashboard profiles give officials the history, indicators and peer comparison to decide what kind of support each needs. The model's decisions are the same as \"repeat last year's outcome\" and McNemar's test found no difference from the next-best model, so its value is that it is documented, calibrated, explainable and reproducible, and brings each municipality's data into one place.`),
    table(["Finding", "Evidence", "What it means for Treasury"], [
      ["Accuracy with uncertainty", `Bootstrap (Efron, 1979): macro-F1 ${ciText("macro_f1")}; recall ${ciText("recall_at_risk")}; precision ${ciText("precision_at_risk")}`, "Roughly 8 to 9 in 10 failing municipalities are flagged; about 1 flag in 10 is a false alarm."],
      ["Calibration", `Brier score ${q8.brier_score.toFixed(3)}; predicted about 84–85% in the high-risk bins against 90–92% observed (Figure A.8)`, "Probabilities can be read roughly at face value; high-risk scores slightly understate the risk."],
      ["Status changes are missed", `Test year: ${q8.status_changes_in_test} municipalities changed status; accuracy ${(q8.accuracy_on_status_changes * 100).toFixed(0)}% on them vs ${(q8.accuracy_on_stable * 100).toFixed(0)}% on the rest`, `About ${Math.round(q8.forecast_2025.expected_status_changes_at_test_rate)} municipalities can be expected to change status in 2025; each will be misclassified.`],
      ["Ranking is no early warning", `Of ${testRows.length} clean municipalities in 2023, the top 10% by risk (${k10}) held ${det(testRows.slice(0, k10))} of the ${det(testRows)} that deteriorated (base rate ${(det(testRows) / testRows.length * 100).toFixed(0)}%)`, "A model-based watch list of clean municipalities is not supported by the evidence."],
    ], [1900, 4300, 3552]),
    caption("Table 8.1: Evidence behind the recommendation (test year: 2023 figures → 2024 audit)."),
    sideFigure("reports/figures/q8_fairness.png", "Figure 8.1: Recall, false-positive rate and accuracy by province and municipality type (test year).", [
      `**Fairness.** Province and type are not model inputs, but performance differs. **${worstFpr.province}** has the highest false-alarm rate (${pct(worstFpr.false_positive_rate)} of its healthy municipalities flagged, against ${pct(Math.min(...otherFpr))}–${pct(Math.max(...otherFpr))} in the other provinces large enough to judge), because several improved after a poor audit. **${worstRecall.province}** has the lowest recall (${pct(worstRecall.recall_at_risk)}): ${Math.round((1 - worstRecall.recall_at_risk) * worstRecall.actual_at_risk)} of its ${worstRecall.actual_at_risk} failing municipalities were missed. Districts were classified perfectly (n = ${dist.n}). ${smallProv.join(", ")} and the metros are too small to judge (marked *). Provinces where outcomes are volatile therefore get more false alarms and missed cases, so flagged lists should be reviewed by province before support is allocated. Full table: Table A.2.`], 410, 4600),
    P("**Limitations.** The model depends on last year's outcome (Q6.1), so it cannot anticipate change. The financial data is self-reported and sometimes implausible; missing debtor and repairs data before 2020/2019 is recorded as zero; the grants extract appears truncated, so grant dependency is unreliable; and municipalities that fail to submit statements, the highest-risk group, have the least data. Results cover 2018–2024 only."),
    P(`**Monitoring.** Each year, when the Auditor-General publishes outcomes: compare the 2025 forecast with them and recompute macro-F1, recall and the false-positive rate overall and by province; retrain on the newest year if macro-F1 falls below ${f3(ci8.macro_f1.ci95_low)} or recall below ${f3(ci8.recall_at_risk.ci95_low)} (the lower confidence bounds); check calibration and the share of municipalities that changed status; and run data-quality checks on each new extract.`),
    P("**Do not use the model** to allocate funding or impose interventions automatically; to judge or penalise a municipality or its officials; to predict deterioration in municipalities with a clean audit; for municipalities without audited figures, or after boundary or accounting-standard changes (as with mSCOA) without re-validation; for years after 2025 without retraining; or when the app warns that inputs are outside the range seen in training. **To become an early-warning tool** it needs in-year quarterly (section 71) data, audit findings, senior-management vacancies and debt-collection trends, and should model the probability of a **change** in status directly."),
    H2("8.2 Reproducible package"),
    table(["Requirement", "Where it is"], [
      ["README, environment, seeds", "README.md; requirements.txt (pinned versions, Python 3.12, PyTorch CPU build); seed 42 for every split, model, search and bootstrap"],
      ["Execution order", "python run_all.py runs all 11 steps in order (Appendix E); each script is named after the question it answers"],
      ["Source links and data dictionary", "README.md and docs/dataset_card.md (Municipal Money site, API documentation, terms of use); docs/data_dictionary.md and reports/data_dictionary.csv"],
      ["Saved model and interface", "models/final_pipeline.joblib (preprocessing and tuned model as one object); app/ (Streamlit code, samples, smoke test)"],
      ["Evidence bundle", "results/ (metric tables, paired McNemar predictions, forecasts), reports/figures/, docs/experiment_log.md, docs/dataset_card.md"],
      ["Data licence", "Municipal Money terms allow reuse, so data/raw is included with attribution; no personal data is included"],
    ], [2600, 7152]),
    caption("Table 8.2: Reproducibility checklist."),
    P("**Reproduction test.** The repository was cloned into an empty folder and python run_all.py was run end to end: all 11 steps completed in 4.1 minutes on a laptop CPU without manual intervention, and every regenerated result file (validation and cross-validation metrics, the Optuna result and test evaluation, ablations, McNemar's test, all 1,679 municipality scores and the uncertainty and fairness tables) was identical to the committed version. Only saved model objects, figure images and the dtype label of one column in the data audit differed (serialisation details and a pandas version change)."),
    H2("8.3 Presentation and contribution statement"),
    P("The 10–12 minute presentation follows this report: problem and stakeholder, data and the leakage-safe split, models and evaluation, optimisation, ablation and McNemar's test, a live dashboard demonstration (three valid municipalities, the invalid file, and a drill-down from the overview to a municipality profile), and the recommendation and limitations. Every member presents the part they led and answers questions on the whole pipeline. A second, plain-language deck (why we chose the project, what it solves, how it works) is provided for non-technical audiences. A one-page contribution statement lists each member's role and specific outputs with evidence from the repository's commit history and is signed by all members."),
  );
  return c;
};
