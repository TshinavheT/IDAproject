// Builds reports/IDA117V_Q4-Q8_Report_Sections.docx from the results files.
// Run from the project root:  node reports/build_report_sections.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType,
  ShadingType, AlignmentType, ImageRun, LevelFormat, BorderStyle, PageBreak, Footer, PageNumber,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const R = (f) => JSON.parse(fs.readFileSync(path.join(ROOT, "results", f), "utf8"));
const csv = (f) => {
  const [head, ...lines] = fs.readFileSync(path.join(ROOT, "results", f), "utf8").trim().split(/\r?\n/);
  const cols = head.split(",");
  return lines.map((l) => Object.fromEntries(l.split(",").map((v, i) => [cols[i], isNaN(+v) ? v : +v])));
};

const q4 = csv("q4_validation_metrics.csv");
const cv = csv("q4_cv_walk_forward.csv");
const gap = csv("q4_overfitting_gap.csv");
const q5 = R("q5_test_result.json");
const mc = R("q6_mcnemar.json");
const abl = csv("q6_ablation.csv");
const dash = R("dashboard_q4.json");

const f3 = (x) => x.toFixed(3);
const pct = (x) => (x * 100).toFixed(1) + "%";
const sgn = (x) => (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(3);

// ---------- building blocks ----------
const FONT = "Calibri";
const CONTENT_W = 9026; // A4 width minus 2 × 1440 margins
const runs = (text) => text.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((s) =>
  s.startsWith("**") ? new TextRun({ text: s.slice(2, -2), bold: true }) : new TextRun(s));
const P = (text, opts = {}) => new Paragraph({ children: runs(text), spacing: { after: 140, line: 276 }, ...opts });
const H1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)], pageBreakBefore: true });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
const B = (text) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(text), spacing: { after: 80 } });
const caption = (text) => new Paragraph({
  children: [new TextRun({ text, italics: true, size: 19, color: "555555" })],
  alignment: AlignmentType.CENTER, spacing: { before: 60, after: 220 },
});

const border = { style: BorderStyle.SINGLE, size: 4, color: "BFC6D4" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(headers, rows, widths, { bold = [] } = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (text, w, header, boldRow) => new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    shading: header ? { fill: "2E3546", type: ShadingType.CLEAR, color: "auto" }
      : boldRow ? { fill: "E8F1FD", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: [new Paragraph({ children: [new TextRun({
      text: String(text), bold: header || boldRow, color: header ? "FFFFFF" : "000000", size: 19,
    })] })],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], true)) }),
      ...rows.map((r, ri) => new TableRow({ children: r.map((v, i) => cell(v, widths[i], false, bold.includes(ri))) })),
    ],
  });
}

function imageSize(file) {
  const buf = fs.readFileSync(file);
  if (buf[0] === 0x89) return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20), type: "png", buf };
  let i = 2; // JPEG: walk segments to the SOF marker
  while (i < buf.length) {
    const marker = buf[i + 1];
    const len = buf.readUInt16BE(i + 2);
    if (marker >= 0xc0 && marker <= 0xc3) return { h: buf.readUInt16BE(i + 5), w: buf.readUInt16BE(i + 7), type: "jpg", buf };
    i += 2 + len;
  }
  throw new Error("Unknown image size: " + file);
}
function figure(rel, text, width = 600) {
  const img = imageSize(path.join(ROOT, rel));
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120 }, children: [new ImageRun({
      type: img.type, data: img.buf, transformation: { width, height: Math.round(width * img.h / img.w) },
      altText: { title: text, description: text, name: path.basename(rel) },
    })] }),
    caption(text),
  ];
}

// ---------- numbers used in the text ----------
const by = Object.fromEntries(q4.map((r) => [r.model, r]));
const cvBy = Object.fromEntries(cv.map((r) => [r.model, r]));
const gapBy = Object.fromEntries(gap.map((r) => [r.model, r]));
const LR = by["Logistic Regression"], RULE = by["Baseline (Repeat last year)"];
const MODELS = q4.map((r) => r.model);
const tm = q5.test_metrics, rm = q5.repeat_last_year_test_metrics;
const [[tn, fp], [fn, tp]] = q5.test_confusion;
const pre = q5.pre_post[0], post = q5.pre_post[1];
const bp = q5.best_params;
const nn = dash.neural_history;
const a = Object.fromEntries(abl.map((r) => [r.experiment.split(":")[0], r]));

const content = [];
const add = (...xs) => xs.flat().forEach((x) => content.push(x));

// ---------- front note ----------
add(
  new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("IDA117V Group Project: Predicting Municipal Audit Outcomes")] }),
  P("**Report sections for Questions 4 to 8.** All numbers are produced by the scripts in the project repository " +
    "(src/evaluate_q4.py, src/optimise_q5.py, src/ablation_mcnemar_q6.py, src/forecast_next.py, src/fairness_q8.py) and the dashboard in app/. Random seed 42 throughout."),
  H2("Note on the Question 3 protocol"),
  P("Before Question 4, the Question 3 models were re-run so that every later comparison uses one consistent, leakage-safe protocol:"),
  B("**Time-based split from Question 2.3.** Training uses feature years 2018–2021 (950 municipality-years), validation uses 2022 (244) " +
    "and the test set is 2023 (240). The first Question 3 run used a random 70/15/15 split, which lets later years inform predictions about earlier ones."),
  B("**Test year kept aside.** The 2023 test year is loaded only once, in Question 5.3, for the final locked model."),
  B("**Feature list from Question 2.4 only.** financial_year_end.year, identifiers and the raw opinion columns are excluded."),
  B("**A second baseline was added:** “repeat last year’s outcome”, which predicts that the year t+1 audit repeats the year t result. " +
    "It learns nothing, so it shows how much skill comes from audit history alone."),
  P("The Question 3 table should therefore be replaced by the validation results in Table 4.1 below. Logistic Regression, not Random Forest, " +
    "is the provisional champion under the corrected protocol."),
);

// ---------- QUESTION 4 ----------
add(
  H1("QUESTION 4: EVALUATION, COMPARISON AND OVERFITTING"),
  H2("4.1 Held-out metrics for every model"),
  P("Every model was fit on the training years (2018–2021) and evaluated on the same 244 municipalities of the 2022 validation year. " +
    "The positive class is at_risk (qualified, adverse, disclaimer or outstanding opinion in year t+1). Macro-F1 is the primary metric because " +
    "both classes matter: missing a failing municipality delays support, while a false alarm wastes scarce Treasury capacity. " +
    `The classes are moderately imbalanced (${pct(dash.val_at_risk_share)} at risk in the validation year), so PR-AUC is reported alongside ROC-AUC; ` +
    "PR-AUC focuses on how well the minority at_risk class is ranked."),
  table(["Model", "Accuracy", "Macro-F1", "Weighted-F1", "Precision (at risk)", "Recall (at risk)", "ROC-AUC", "PR-AUC"],
    q4.map((r) => [r.model, f3(r.val_accuracy), f3(r.val_macro_f1), f3(r.val_weighted_f1), f3(r.val_precision_at_risk),
      f3(r.val_recall_at_risk), f3(r.val_roc_auc), f3(r.val_pr_auc)]),
    [2066, 980, 980, 1000, 1000, 1000, 1000, 1000], { bold: [2] }),
  caption("Table 4.1: Validation-year (2022) metrics for both baselines and the four substantive models (n = 244)."),
  P(`All four substantive models clearly beat the majority-class baseline (macro-F1 ${f3(by["Baseline (Dummy)"].val_macro_f1)}). ` +
    `However, the “repeat last year” baseline already reaches macro-F1 ${f3(RULE.val_macro_f1)}, the same as the best model. ` +
    `Logistic Regression agreed with that rule on 100% of validation municipalities, and the other models agreed on 97–98%. ` +
    `The models therefore mainly learn that audit outcomes persist. Where they differ from the rule is in ranking: ` +
    `Logistic Regression and the neural networks reach ROC-AUC 0.927–0.929 against ${f3(RULE.val_roc_auc)} for the rule, ` +
    `because the financial ratios separate stronger and weaker municipalities within each outcome group.`),

  H2("4.2 Classification reports, confusion matrices and ROC curves"),
  P("Table 4.2 gives the per-class classification report for every substantive model, with class labels and support. " +
    "Figure 4.1 shows the six confusion matrices, Figure 4.2 overlays all ROC curves on one figure, and Figure 4.3 shows the precision–recall curves."),
  table(["Model", "Class", "Precision", "Recall", "F1", "Support"], [
    ["Logistic Regression", "not_at_risk", "0.907", "0.901", "0.904", "141"],
    ["", "at_risk", "0.865", "0.874", "0.870", "103"],
    ["Random Forest", "not_at_risk", "0.900", "0.894", "0.897", "141"],
    ["", "at_risk", "0.856", "0.864", "0.860", "103"],
    ["MLP", "not_at_risk", "0.912", "0.879", "0.895", "141"],
    ["", "at_risk", "0.843", "0.883", "0.863", "103"],
    ["Residual Tabular NN", "not_at_risk", "0.912", "0.879", "0.895", "141"],
    ["", "at_risk", "0.843", "0.883", "0.863", "103"],
    ["Baseline (Dummy)", "not_at_risk", "0.578", "1.000", "0.732", "141"],
    ["", "at_risk", "0.000", "0.000", "0.000", "103"],
    ["Baseline (Repeat last year)", "not_at_risk", "0.907", "0.901", "0.904", "141"],
    ["", "at_risk", "0.865", "0.874", "0.870", "103"],
  ], [2626, 1400, 1250, 1250, 1250, 1250]),
  caption("Table 4.2: Per-class classification reports on the validation year (full reports in results/q4_classification_reports.txt)."),
  figure("reports/figures/q4_confusion_matrices.png", "Figure 4.1: Confusion matrices for all models, validation year 2022."),
  P("Logistic Regression misses 13 of the 103 at-risk municipalities (false negatives) and raises 14 false alarms. " +
    "The two neural networks catch slightly more at-risk municipalities (91, recall 0.883) at the cost of more false alarms (17). " +
    "The dummy baseline never flags anyone, which is why its accuracy (0.578) looks acceptable while its at-risk recall is zero; " +
    "this is exactly why accuracy alone is not used to judge the models."),
  figure("reports/figures/q4_roc_curves.png", "Figure 4.2: ROC curves for all models on one figure (validation 2022, positive class at_risk).", 470),
  figure("reports/figures/q4_pr_curves.png", "Figure 4.3: Precision–recall curves (validation 2022).", 470),

  H2("4.3 Model comparison and provisional champion"),
  P("Variability was estimated with walk-forward (expanding-window) cross-validation inside the training years: train on 2018 and score 2019, " +
    "train on 2018–2019 and score 2020, train on 2018–2020 and score 2021. A time-respecting design was used instead of random k-fold so that a model " +
    "is never scored on a year earlier than the data it learned from."),
  table(["Model", "Val macro-F1", "Val ROC-AUC", "CV macro-F1 mean", "CV SD", "Fold 2019", "Fold 2020", "Fold 2021"],
    MODELS.map((m) => [m, f3(by[m].val_macro_f1), f3(by[m].val_roc_auc), f3(cvBy[m].cv_macro_f1_mean), f3(cvBy[m].cv_macro_f1_std),
      f3(cvBy[m].fold_2019_macro_f1), f3(cvBy[m].fold_2020_macro_f1), f3(cvBy[m].fold_2021_macro_f1)]),
    [2266, 1000, 1000, 1110, 850, 900, 900, 1000], { bold: [2] }),
  caption("Table 4.3: Validation scores and walk-forward cross-validation (macro-F1) for every model."),
  figure("reports/figures/q4_model_comparison.png", "Figure 4.4: Model comparison: validation scores (left) and cross-validation mean ± SD (right)."),
  P(`**Provisional champion: Logistic Regression**, selected on validation performance only (the test year was not used). ` +
    `It has the highest validation macro-F1 among the substantive models (${f3(LR.val_macro_f1)}), the highest PR-AUC (${f3(LR.val_pr_auc)}) and ` +
    `stable cross-validation (${f3(cvBy["Logistic Regression"].cv_macro_f1_mean)} ± ${f3(cvBy["Logistic Regression"].cv_macro_f1_std)}). ` +
    `The MLP and residual network tie for second on macro-F1 (${f3(by["MLP"].val_macro_f1)}), but their cross-validation is unstable ` +
    `(SD ≈ 0.18–0.20): in the fold trained only on 2018–2019 (about 470 rows) their macro-F1 collapsed to 0.54 and 0.52. ` +
    `With fewer than 1,000 rows of tabular data, the simpler linear model is the more reliable choice. ` +
    `The two baselines are reported for context but are not eligible as the champion.`),

  H2("4.4 Overfitting diagnosis and controls"),
  table(["Model", "Train macro-F1", "Validation macro-F1", "Gap (train − val)"],
    gap.map((r) => [r.model, f3(r.train_macro_f1), f3(r.val_macro_f1), sgn(r.macro_f1_gap)]),
    [3226, 1900, 1950, 1950], { bold: [3] }),
  caption("Table 4.4: Train-versus-validation macro-F1 gap for every model."),
  figure("reports/figures/q4_learning_curves.png", "Figure 4.5: Learning curves (training vs validation macro-F1 as the training set grows)."),
  figure("reports/figures/q4_neural_training_curves.png", "Figure 4.6: Neural networks: training vs early-stopping loss and accuracy per epoch.", 560),
  P(`**Random Forest overfits.** It scores 1.000 on the training years but ${f3(gapBy["Random Forest"].val_macro_f1)} on validation, a gap of ` +
    `${f3(gapBy["Random Forest"].macro_f1_gap)}, and its learning curve stays at 1.0 for every training size (Figure 4.5). Fully grown trees memorise ` +
    `the training rows; limiting max_depth or raising min_samples_leaf would reduce this, but Random Forest was not selected, so it was not tuned further.`),
  P("**Logistic Regression and both neural networks show no meaningful overfitting.** Their gaps are slightly negative (−0.010 to −0.022), " +
    "meaning validation scores are a little higher than training scores. This is because the 2022 validation year is slightly easier: " +
    "the repeat-last-year rule itself scores 0.887 in 2022 against 0.865 across 2018–2021. Their learning curves flatten after about 400 rows, " +
    "so more data of the same kind would add little."),
  P(`**Controls used.** Logistic Regression uses regularisation (L2 by default, L1 after tuning). The neural networks use dropout of 0.2, ` +
    `class-weighted cross-entropy, weight decay of 0.0001 (residual network) and early stopping with patience 10. Early stopping monitors a ` +
    `15% stratified slice of the training years, not the validation year, so the validation year stays clean for model selection. ` +
    `The MLP's best epoch was ${nn.MLP.best_epoch} (stopped at ${nn.MLP.epochs_run}) and the residual network's best epoch was ` +
    `${nn["Residual Tabular NN"].best_epoch} (stopped at ${nn["Residual Tabular NN"].epochs_run}). In Figure 4.6 the training and ` +
    `early-stopping losses level off together without diverging, which confirms the networks stopped before memorising.`),
);

// ---------- QUESTION 5 ----------
add(
  H1("QUESTION 5: CHAMPION OPTIMISATION"),
  H2("5.1 Search method, search space and scoring rule"),
  P(`Only the validation champion, Logistic Regression, was optimised. The search used **Optuna** with the Tree-structured Parzen Estimator ` +
    `sampler (seed 42) for **${q5.n_trials} trials**. Trial 0 was fixed to the untuned Question 3/4 configuration so the default appears in the search history.`),
  table(["Hyperparameter", "Search range", "Why it was searched"], [
    ["C (inverse regularisation)", "0.001 – 100, log scale", "Controls how strongly coefficients are shrunk"],
    ["Penalty", "L2, L1, elastic-net", "L1 can switch off weak features entirely"],
    ["l1_ratio", "0.05 – 0.95 (elastic-net only)", "Mix of L1 and L2 shrinkage"],
    ["Class weight", "balanced, none", "Imbalance treatment"],
    ["Scaler", "standard, robust", "Robust scaling is less sensitive to the outliers found in Question 2.1"],
  ], [2600, 2600, 3826]),
  caption("Table 5.1: Optuna search space for Logistic Regression."),
  P("**Scoring rule:** the mean macro-F1 across the three walk-forward folds inside the training years (2019, 2020 and 2021)."),

  H2("5.2 Validation protocol and before/after comparison"),
  P("Tuning never saw the 2022 validation year or the 2023 test year: every trial was scored only on folds drawn from 2018–2021. " +
    "The validation year was used afterwards only to report the before/after comparison."),
  table(["Configuration", "CV macro-F1 (mean ± SD)", "Val accuracy", "Val macro-F1", "Val recall (at risk)", "Val ROC-AUC", "Val PR-AUC"], [
    ["Default (C = 1, L2, balanced)", `${f3(pre.cv_macro_f1_mean)} ± ${f3(pre.cv_macro_f1_std)}`, f3(pre.val_accuracy), f3(pre.val_macro_f1),
      f3(pre.val_recall_at_risk), f3(pre.val_roc_auc), f3(pre.val_pr_auc)],
    [`Tuned (C = ${bp.C.toFixed(3)}, ${bp.penalty.toUpperCase()}, ${bp.class_weight})`, `${f3(post.cv_macro_f1_mean)} ± ${f3(post.cv_macro_f1_std)}`,
      f3(post.val_accuracy), f3(post.val_macro_f1), f3(post.val_recall_at_risk), f3(post.val_roc_auc), f3(post.val_pr_auc)],
  ], [2426, 1500, 1000, 1000, 1100, 1000, 1000], { bold: [1] }),
  caption("Table 5.2: Logistic Regression before and after optimisation."),
  P(`**Chosen hyperparameters:** C = ${bp.C.toFixed(4)}, penalty = ${bp.penalty}, class_weight = ${bp.class_weight}, scaler = ${bp.scaler}.`),
  figure("reports/figures/q5_optimisation_history.png", "Figure 5.1: Optuna optimisation history (each dot is one trial; the line is the best so far).", 540),
  P(`Optimisation improved the cross-validation macro-F1 by only ${sgn(post.cv_macro_f1_mean - pre.cv_macro_f1_mean)}, which is smaller than the ` +
    `fold-to-fold standard deviation (≈ 0.025), so it is not a meaningful improvement. Validation macro-F1 did not change, and validation ` +
    `ROC-AUC fell slightly (${f3(pre.val_roc_auc)} → ${f3(post.val_roc_auc)}) because the search optimised macro-F1, not ranking. ` +
    `The tuned configuration was kept because the scoring rule was fixed before the search. The main practical effect of tuning is a ` +
    `**simpler model**: the L1 penalty set five of the nine financial ratios to exactly zero (Table 5.3).`),
  table(["Feature (standardised)", "Coefficient", "Effect on risk"], [
    ["Last year's outcome = at_risk", "+1.688", "Raises risk strongly"],
    ["Last year's outcome = not_at_risk", "−1.710", "Lowers risk strongly"],
    ["Cash coverage ratio", "−0.145", "More months of cash → lower risk"],
    ["Repairs & maintenance ratio", "−0.115", "More maintenance spending → lower risk"],
    ["Operating surplus", "−0.100", "Larger surplus → lower risk"],
    ["Total revenue", "−0.029", "Larger municipalities → slightly lower risk"],
    ["Expenditure, collection rate, debtor days, grant dependency, irregular expenditure", "0.000", "Removed by the L1 penalty"],
  ], [4026, 1500, 3500]),
  caption("Table 5.3: Coefficients of the final tuned model (fit on 2018–2022)."),

  H2("5.3 Final locked pipeline: one-time test evaluation"),
  P(`The tuned pipeline (preprocessing and model together) was locked, refit on 2018–2022 and evaluated **once** on the ${q5.n_test} municipalities ` +
    `of the 2023 test year (predicting their 2024 audit outcome). It is saved as models/final_pipeline.joblib and is the exact object loaded by the user interface.`),
  table(["Model", "Accuracy", "Macro-F1", "Precision (at risk)", "Recall (at risk)", "ROC-AUC", "PR-AUC"], [
    ["Tuned Logistic Regression (locked)", f3(tm.accuracy), f3(tm.macro_f1), f3(tm.precision_at_risk), f3(tm.recall_at_risk), f3(tm.roc_auc), f3(tm.pr_auc)],
    ["Repeat-last-year rule (reference)", f3(rm.accuracy), f3(rm.macro_f1), f3(rm.precision_at_risk), f3(rm.recall_at_risk), f3(rm.roc_auc), f3(rm.pr_auc)],
  ], [2826, 1000, 1000, 1100, 1100, 1000, 1000], { bold: [0] }),
  caption("Table 5.4: The single test-set evaluation (2023 → 2024, n = 240)."),
  figure("reports/figures/q5_test_confusion_matrix.png", "Figure 5.2: Confusion matrix of the locked model on the test year.", 360),
  P(`On unseen data the model is accurate (${pct(tm.accuracy)}) and generalises without loss: test macro-F1 (${f3(tm.macro_f1)}) is at least as high as ` +
    `validation (${f3(post.val_macro_f1)}). It caught ${tp} of the ${tp + fn} municipalities whose next audit was poor and raised ${fp} false alarms among ${tn + fp} healthy ones.`),
  P(`**Is the improvement practically meaningful?** Against the baselines, only partly. The tuning gain itself is negligible (Question 5.2). The locked model's ` +
    `yes/no predictions on the test year are identical to the repeat-last-year rule, and its test ROC-AUC (${f3(tm.roc_auc)}) is slightly ` +
    `lower than the rule's (${f3(rm.roc_auc)}), while PR-AUC is slightly higher (${f3(tm.pr_auc)} vs ${f3(rm.pr_auc)}). The ranking advantage seen ` +
    `on validation therefore did not clearly hold on the test year. **All 22 test errors are municipalities whose status changed**: the ${fn} missed ` +
    `municipalities were not at risk in 2023 but failed in 2024, and the ${fp} false alarms improved. The practical value of the model is a consistent, ` +
    `explainable and documented risk score for prioritising support, not better detection of sudden deterioration, which remains the key limitation.`),
);

// ---------- QUESTION 6 ----------
const ablRows = [
  ["Full tuned champion (reference)", a["Full tuned champion (reference)"]],
  ["A1: remove audit-history feature (prior_audit_outcome)", a["A1"]],
  ["A2: remove financial-ratio feature group (9 ratios)", a["A2"]],
  ["A3: remove imbalance treatment (class weighting)", a["A3"]],
  ["A4: remove scaling step", a["A4"]],
  ["A5: swap L1 regulariser for L2", a["A5"]],
];
add(
  H1("QUESTION 6: ABLATION STUDY AND STATISTICAL VALIDATION"),
  H2("6.1 Controlled ablations"),
  P("Five ablations were run on the tuned champion. Each changes exactly one component while the split (fit on 2018–2021), random seed (42) and " +
    "evaluation protocol (2022 validation year plus walk-forward cross-validation) stay fixed. The 2023 test year was not reused."),
  table(["Experiment", "Val macro-F1", "Δ macro-F1", "Val ROC-AUC", "Δ ROC-AUC", "Val recall (at risk)", "CV macro-F1"],
    ablRows.map(([name, r]) => [name, f3(r.val_macro_f1), sgn(r.delta_val_macro_f1), f3(r.val_roc_auc), sgn(r.delta_val_roc_auc),
      f3(r.val_recall_at_risk), f3(r.cv_macro_f1_mean)]),
    [3026, 950, 950, 950, 950, 1100, 1100], { bold: [0] }),
  caption("Table 6.1: Ablation results. Δ is the change relative to the full tuned champion."),
  figure("reports/figures/q6_ablation.png", "Figure 6.1: Change in validation macro-F1 and ROC-AUC for each ablation.", 560),
  B(`**A1, remove audit history:** macro-F1 falls by ${f3(-a["A1"].delta_val_macro_f1)} and ROC-AUC by ${f3(-a["A1"].delta_val_roc_auc)}. ` +
    `This is the model's main dependency. The ratios alone still reach macro-F1 ${f3(a["A1"].val_macro_f1)}, well above the dummy baseline (0.366), so they carry real but weaker signal.`),
  B(`**A2, remove all financial ratios:** macro-F1 is unchanged, but ROC-AUC falls by ${f3(-a["A2"].delta_val_roc_auc)}. The ratios do not change ` +
    `any yes/no decision; they only refine the ordering of municipalities within each outcome group.`),
  B(`**A3, remove class weighting:** no change. The 58/42 class split is mild enough that imbalance treatment is unnecessary for this model.`),
  B(`**A4, remove scaling:** the largest drop (macro-F1 ${sgn(a["A4"].delta_val_macro_f1)}, ROC-AUC ${sgn(a["A4"].delta_val_roc_auc)}). ` +
    `Revenue and expenditure are measured in billions of rand, so without standardisation the L1 penalty shrinks the useful features unevenly. ` +
    `Correct preprocessing is the second critical component.`),
  B(`**A5, L2 instead of L1:** macro-F1 is unchanged and ROC-AUC is ${sgn(a["A5"].delta_val_roc_auc)}. The regulariser type matters little for accuracy; ` +
    `L1 was kept because it produces a smaller model that is easier to explain.`),
  P("**What the system depends on:** first, last year's audit outcome; second, correct scaling of the inputs. The financial ratios add only " +
    "ranking information, and the imbalance treatment and regulariser choice are not important."),

  H2("6.2 McNemar's test: champion vs strongest comparator"),
  P(`The optimised champion was compared with the strongest comparator, the **MLP**. It tied with the residual network for the best non-champion ` +
    `validation macro-F1 and had the higher ROC-AUC. Both models were fit on 2018–2022 and predicted the **same ${mc.n_test} test municipalities**. ` +
    `Paired predictions are saved in results/q6_paired_test_predictions.csv.`),
  table(["", "MLP correct", "MLP wrong", "Total"], [
    ["Champion correct", String(mc.table.both_correct), String(mc.table.champion_only_correct), String(mc.table.both_correct + mc.table.champion_only_correct)],
    ["Champion wrong", String(mc.table.comparator_only_correct), String(mc.table.both_wrong), String(mc.table.comparator_only_correct + mc.table.both_wrong)],
    ["Total", String(mc.table.both_correct + mc.table.comparator_only_correct), String(mc.table.champion_only_correct + mc.table.both_wrong), String(mc.n_test)],
  ], [2826, 2100, 2100, 2000]),
  caption("Table 6.2: McNemar 2 × 2 correctness table on the test year (b = champion only correct, c = MLP only correct)."),
  B("**H₀:** the two models have the same error rate on these municipalities, so discordant cases are equally likely in either direction (P(b) = P(c))."),
  B("**H₁:** the error rates differ (P(b) ≠ P(c)), two-sided."),
  B(`**Significance level:** α = ${mc.alpha}.`),
  B(`**Test:** there is only ${mc.discordant_pairs} discordant pair (b = ${mc.table.champion_only_correct}, c = ${mc.table.comparator_only_correct}), far below the ` +
    `usual threshold of 25, so the **exact binomial** version was used instead of the chi-square approximation. Statistic = min(b, c) = ` +
    `${mc.statistic.toFixed(0)}, **exact p-value = ${mc.p_value.toFixed(4)}**.`),
  B(`**Decision:** p > 0.05, so **H₀ is not rejected**.`),
  P(`**Statistical vs practical significance.** There is no statistical evidence that the tuned champion is more accurate than the MLP; ` +
    `the two models disagree on a single municipality. The practical difference is also negligible: accuracy ${pct(mc.champion_accuracy)} vs ` +
    `${pct(mc.comparator_accuracy)} and macro-F1 ${f3(mc.champion_macro_f1)} vs ${f3(mc.comparator_macro_f1)}. Choosing Logistic Regression is ` +
    `justified by simplicity, explainability (Table 5.3) and stability (cross-validation SD 0.025 vs 0.18), not by superior accuracy. ` +
    `For the same reason, a McNemar test against the repeat-last-year rule is uninformative: the two produce identical predictions (b = c = 0).`),
);

// ---------- QUESTION 7 ----------
// Numbers for the drill-down and forecast text come from results/municipality_scores.csv.
function readCsv(file) {
  const text = fs.readFileSync(file, "utf8").trim();
  const rows = [];
  let row = [], cell = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(cell); rows.push(row); row = []; cell = "";
    } else cell += ch;
  }
  row.push(cell); rows.push(row);
  const [head, ...body] = rows;
  return body.map((r) => Object.fromEntries(r.map((v, i) => [head[i], v])));
}
const scores = readCsv(path.join(ROOT, "results", "municipality_scores.csv"));
const fc = scores.filter((r) => r.split === "forecast");
const fcFlagged = fc.filter((r) => r.predicted_outcome === "at_risk").length;
const fcHigh = fc.filter((r) => +r.risk_probability >= 0.8).length;
const fcChanging = fc.filter((r) => r.predicted_outcome !== r.prior_audit_outcome).length;
const emf = fc.find((r) => r["demarcation.code"] === "GT421");
const emfRank = fc.filter((r) => +r.risk_probability > +emf.risk_probability).length + 1;
const gp = fc.filter((r) => r.province === emf.province);
const emfProvRank = gp.filter((r) => +r.risk_probability > +emf.risk_probability).length + 1;
const recallMissed = scores.filter((r) => r.split === "test" && r.actual_next_outcome === "at_risk" && r.predicted_outcome === "not_at_risk").length;

add(
  H1("QUESTION 7: USER-INTERFACE DEPLOYMENT"),
  H2("7.1 Working user interface"),
  P("The final optimised model is deployed as an interactive **Streamlit** web application (app/app.py, Streamlit 1.65) styled as a " +
    "KPI dashboard. It has six pages, and every number on the overview can be opened for more detail:"),
  B("**Overview:** test-year model KPIs (macro-F1, recall, precision and ROC-AUC rings), the forecast for the next audit, the at-risk trend by audit year, the ten highest-risk municipalities, a province snapshot and the model leaderboard."),
  B("**Explorer:** filter all municipalities by audit year (2019–2025), province, type (metro, district or local), last audit opinion and risk band."),
  B("**Municipality profile:** one page per municipality with its forecast, history, financial health and peer comparison."),
  B("**Risk check:** the prediction tool for a chosen municipality, manually entered figures or an uploaded CSV."),
  B("**Model evidence** and **About & responsible use:** the Question 4–6 evidence, the limitations and when not to use the model."),
  figure("reports/figures/app/app_overview_full.png", "Figure 7.1: Overview page. Every ring, gauge and chart is clickable.", 470),

  H2("7.2 Input, prediction pipeline and output"),
  P("Every prediction runs the saved end-to-end pipeline (models/final_pipeline.joblib), so imputation, scaling, encoding and the tuned " +
    "model behave exactly as in Question 5. Nothing is retrained in the app. Users can provide input in three ways:"),
  B("**Pick a municipality:** its latest audited figures (2024) are scored to forecast the 2025 audit, with a link to its full profile."),
  B("**Enter figures:** a form for every feature, with units and help text (revenue and expenditure in rand millions, ratios as percentages). The operating surplus is calculated automatically."),
  B("**Upload CSV:** score up to 500 municipalities at once; results are sorted by risk and can be downloaded."),
  P("Each prediction shows the predicted class (At risk / Not at risk), the probability of a poor audit on a gauge, a confidence band " +
    "(high, moderate or close call around the 50% threshold) and a plain-language explanation of the two or three features that pushed " +
    "the prediction most, computed as coefficient × standardised value."),
  P(`**Forecasting the next audit.** The raw Municipal Money extracts already contain audited 2024 financial statements and 2024 audit ` +
    `opinions, so src/forecast_next.py rebuilds the features for every year from 2018 to 2024 with the same feature-engineering code used for ` +
    `the modelling dataset. Before scoring, it checks that the rebuilt 2018–2023 features match modeling_dataset.csv exactly ` +
    `(1,434 of 1,434 rows) and that the 2023 scores match the Question 5 test predictions. It then scores every municipality-year with the ` +
    `locked pipeline. The ${fc.length} rows for 2024 give a genuine forecast of the **2025 audit**, whose outcome is not yet published: ` +
    `**${fcFlagged}** municipalities are forecast to be at risk, ${fcHigh} of them with a probability of 80% or more.`),
  P("**Municipality profile.** Clicking any municipality opens its profile (Figures 7.2 and 7.3), which can also be shared as a link " +
    "(for example /municipality?code=GT421). The profile shows:"),
  B("the forecast for the next audit, with its gauge, explanation, national rank, province rank and how many years the current outcome has lasted;"),
  B("the **risk history**: the model's probability for every audit year from 2019 to 2025, with markers coloured by what actually happened. " +
    "The years the model was trained on are shaded, so in-sample points are not mistaken for genuine forecasts;"),
  B("the Auditor-General opinion for every year, six financial-health trends (cash coverage, collection rate, debtor days, repairs and " +
    "maintenance, irregular expenditure and operating surplus) against the national median, and a peer table comparing the latest figures " +
    "with the province, municipality-type and national medians and the MFMA Circular 71 norms."),
  figure("reports/figures/app/app_profile_top.png", `Figure 7.2: Profile of Emfuleni (GT421): ${(+emf.risk_probability * 100).toFixed(1)}% forecast risk for the 2025 audit, ranked #${emfRank} of ${fc.length} nationally and #${emfProvRank} of ${gp.length} in ${emf.province}, with its risk history and audit opinions.`, 520),
  figure("reports/figures/app/app_profile_trends.png", "Figure 7.3: Financial-health trends against the national median, and the peer comparison against Treasury norms.", 520),
  P("**Drill-downs.** Table 7.1 lists what each element of the dashboard opens. Every list of municipalities is clickable and leads to that municipality's profile."),
  table(["Click on", "Opens"], [
    ["Macro-F1 ring → Details", "Precision, recall and F1 for each class in the 2024 test year"],
    ["Recall ring → Details", `The at-risk municipalities that were caught and the ${recallMissed} that were missed, with their before-and-after opinions`],
    ["Precision ring → Details", "The correct flags and the false alarms"],
    ["ROC-AUC ring → Details", "How predicted risk is spread for municipalities that did and did not fail"],
    ["Forecast gauges → See list", `The ${fcFlagged} municipalities flagged for 2025, the ${fcHigh} at 80% or more, and those forecast to change status (${fcChanging})`],
    ["A point on the trend chart", "That audit year's opinion breakdown and at-risk share by province"],
    ["A top-10 bar", "That municipality's profile"],
    ["A province bar", "The Explorer, filtered to that province"],
    ["A leaderboard bar", "That model's confusion matrix and cross-validation folds"],
    ["Explorer category bar or table row", "Filters the Explorer, or opens the municipality's profile"],
  ], [3200, 5826]),
  caption("Table 7.1: Drill-down interactions in the dashboard."),
  figure("reports/figures/app/app_dialog_recall.png", `Figure 7.4: Recall details: the ${recallMissed} at-risk municipalities the model missed in the test year, all of which had a clean audit the year before.`, 520),
  figure("reports/figures/app/app_explorer.png", "Figure 7.5: Explorer with clickable category charts, the municipality table and the biggest risk increases.", 470),
  P(`The forecast also shows the model's main limitation to its users: **${fcChanging === 0 ? "no" : fcChanging} municipalit${fcChanging === 1 ? "y is" : "ies are"} ` +
    `forecast to change status** between the 2024 and 2025 audits. The dashboard states this on the overview rather than hiding it, because ` +
    `municipalities whose outcome changes are exactly the cases the model cannot anticipate.`),

  H2("7.3 Input validation and safeguards"),
  table(["Check", "Response"], [
    ["Text where a number is expected", "Error naming the row and field; row is not scored"],
    ["Revenue or expenditure missing, zero or negative", "Error; row is not scored"],
    ["Unrecognised audit outcome", "Error listing the accepted values (at_risk / not_at_risk or an AGSA opinion)"],
    ["Required columns missing from a CSV, empty file, or more than 500 rows", "Error explaining the expected format"],
    ["Ratio left blank", "Warning; filled with the training median (shown to the user)"],
    ["Value outside the 1st–99th percentile of training data", "Warning that the prediction needs extra caution (also shown for picked municipalities)"],
    ["Operating surplus inconsistent with revenue − expenditure", "Warning; recalculated"],
  ], [4513, 4513]),
  caption("Table 7.2: Input validation rules in the interface."),
  P("**Guidance:** a column guide and help tooltips explain every feature, its unit and the relevant Treasury norm. " +
    "**Responsible use:** every prediction carries a notice that a flag means “look closer and offer support”, not “this municipality has failed”. " +
    "The profile's peer table warns that raw Municipal Money figures can contain reporting errors, and the About page states the limitations. " +
    "**Privacy:** the app needs no credentials or API keys, stores nothing, and the data contains no personal information."),
  figure("reports/figures/app/app_invalid_input.jpg", "Figure 7.6: Invalid manual input (total expenditure = 0) rejected with a clear error message.", 520),

  H2("7.4 Deployment instructions and demonstration"),
  P("The app runs locally from the repository with these commands (documented in README.md):"),
  ...["python -m venv .venv", ".venv\\Scripts\\activate", "pip install torch --index-url https://download.pytorch.org/whl/cpu",
    "pip install -r requirements.txt", "streamlit run app/app.py"].map((c) => new Paragraph({
    children: [new TextRun({ text: c, font: "Consolas", size: 19 })], spacing: { after: 40 }, indent: { left: 360 } })),
  P("It then opens at http://localhost:8501. The forecast file (results/municipality_scores.csv) is included in the repository and can be " +
    "regenerated with python src/forecast_next.py. A smoke test (python app/test_app.py) opens every page and every drill-down dialog " +
    "and fails if any of them raises an error; all 19 checks pass. The demonstration files are in app/samples/:",
    { spacing: { before: 140, after: 140 } }),
  table(["Case", "Input", "Output"], [
    ["Valid 1: Masilonyana (FS181)", "Prior opinion disclaimer, cash coverage −23.7 months, irregular expenditure 1,271%", "At risk, 89.9%, high confidence (warnings for unusual values)"],
    ["Valid 2: eThekwini (ETH)", "Prior opinion unqualified (with findings), revenue R48.9 bn, cash coverage 0.9 months", "Not at risk, 9.2%, high confidence"],
    ["Valid 3: Tsantsabane (NC085)", "Prior opinion qualified, cash coverage 0.4 months, repairs & maintenance 30.6%", "At risk, 77.2%, moderate confidence"],
    ["Invalid: invalid_case.csv", "Revenue “four hundred million”, expenditure 0, prior outcome “maybe”", "Rejected with three specific error messages; nothing scored"],
  ], [2500, 3500, 3026]),
  caption("Table 7.3: Demonstration cases (the sample CSV uses 2023 figures, i.e. predictions for the 2024 audit): three valid and one invalid."),
);

// ---------- QUESTION 8 ----------
const q8 = R("q8_uncertainty.json");
const fprov = csv("q8_fairness_province.csv");
const ftype = csv("q8_fairness_type.csv");
const ci8 = q8.metrics_ci95;
const ciText = (k) => `${f3(ci8[k].estimate)} (95% CI ${f3(ci8[k].ci95_low)}–${f3(ci8[k].ci95_high)})`;
const reliableProv = fprov.filter((r) => r.reliable === "True" || r.reliable === true);
const worstFpr = reliableProv.reduce((a, b) => (b.false_positive_rate > a.false_positive_rate ? b : a));
const worstRecall = reliableProv.reduce((a, b) => (b.recall_at_risk < a.recall_at_risk ? b : a));
const smallProv = fprov.filter((r) => !(r.reliable === "True" || r.reliable === true)).map((r) => r.province);
const otherFpr = reliableProv.filter((r) => r.province !== worstFpr.province).map((r) => r.false_positive_rate);
const dist = ftype.find((r) => r.category === "District");

// Watch-list check: does the model's ranking among currently clean municipalities find the ones that deteriorate?
const testRows = scores.filter((r) => r.split === "test" && r.prior_audit_outcome === "not_at_risk")
  .sort((a, b) => +b.risk_probability - +a.risk_probability);
const k10 = Math.round(testRows.length * 0.1);
const det = (rows) => rows.filter((r) => r.actual_next_outcome === "at_risk").length;
const detAll = det(testRows), detTop = det(testRows.slice(0, k10));

add(
  H1("QUESTION 8: RECOMMENDATION, REPRODUCIBILITY AND TEAM DEFENCE"),
  H2("8.1 Recommendation for National Treasury"),
  P(`**Recommendation.** National Treasury's local government support function should use the model as a **consistent, explainable ` +
    `triage list for municipalities that are already in difficulty**, not as an early-warning system. For the 2025 audit it flags ` +
    `**${q8.forecast_2025.flagged} of ${q8.forecast_2025.n}** municipalities, ${fcHigh} of them with a probability of 80% or more. These are ` +
    `the municipalities where support (finance secondments, closer oversight and Financial Management Grant conditions) is most ` +
    `likely to be needed. The dashboard's profiles give officials the history, financial indicators and peer comparison to decide what ` +
    `kind of support each one needs. Detecting municipalities that are about to deteriorate needs a different approach (see below).`),
  P("**Why not more than that.** The evidence from Questions 4–6 is consistent: the model's decisions are the same as the rule " +
    "“repeat last year's audit outcome”, and McNemar's test found no difference from the next-best model. Its value is that it is " +
    "documented, calibrated, explainable and reproducible, and that it brings each municipality's data into one place."),
  table(["Finding", "Evidence", "What it means for Treasury"], [
    ["Accuracy with uncertainty", `Macro-F1 ${ciText("macro_f1")}; recall ${ciText("recall_at_risk")}; precision ${ciText("precision_at_risk")}`,
      "Roughly 8 in 10 to 9 in 10 failing municipalities are flagged; about 1 flag in 10 is a false alarm."],
    ["Calibration", `Brier score ${q8.brier_score.toFixed(3)}; predicted ≈ 84–85% in the high-risk bins vs 90–92% observed`,
      "Probabilities can be read roughly at face value; high-risk scores slightly understate the risk."],
    ["Status changes are missed", `Test year: ${q8.status_changes_in_test} municipalities changed status; accuracy ${(q8.accuracy_on_status_changes * 100).toFixed(0)}% on them vs ${(q8.accuracy_on_stable * 100).toFixed(0)}% on the rest`,
      `About ${Math.round(q8.forecast_2025.expected_status_changes_at_test_rate)} municipalities can be expected to change status in 2025, and every one will be misclassified.`],
    ["Ranking does not give an early warning", `Of the ${testRows.length} clean municipalities in 2023, the top 10% by risk (${k10}) contained ${detTop} of the ${detAll} that deteriorated (base rate ${(detAll / testRows.length * 100).toFixed(0)}%)`,
      "A model-based watch list of clean municipalities is not supported by the evidence."],
    ["No close calls", `${q8.forecast_2025.close_calls_40_60} of ${q8.forecast_2025.n} forecasts fall between 40% and 60%`,
      "High confidence reflects persistence, not certainty about each municipality's finances."],
  ], [2000, 3700, 3326]),
  caption("Table 8.1: Evidence behind the recommendation (test year: 2023 figures → 2024 audit)."),
  P(`**Fairness.** Province and municipality type are not model inputs, but performance differs across them (Figure 8.1, Table 8.2). ` +
    `**${worstFpr.province}** has the highest false-alarm rate (${pct(worstFpr.false_positive_rate)} of its healthy municipalities flagged, ` +
    `against ${pct(Math.min(...otherFpr))}–${pct(Math.max(...otherFpr))} in the other provinces large enough to judge), because several of its municipalities improved after a poor audit. ` +
    `**${worstRecall.province}** has the lowest recall (${pct(worstRecall.recall_at_risk)}): ${Math.round((1 - worstRecall.recall_at_risk) * worstRecall.actual_at_risk)} of its ` +
    `${worstRecall.actual_at_risk} failing municipalities were missed. District municipalities were classified perfectly (n = ${dist.n}). ` +
    `${smallProv.join(", ")} and the metros have too few municipalities, or too few in one class, to judge reliably. ` +
    `The risk is unequal attention: provinces where outcomes are volatile get more false alarms and more missed cases, so flagged ` +
    `lists should be reviewed by province before support is allocated.`),
  table(["Province", "n", "Actually at risk", "Flagged", "Accuracy", "Recall", "False-positive rate", "Judge?"],
    fprov.map((r) => [r.province, String(r.n), String(r.actual_at_risk), pct(r.flagged_share), pct(r.accuracy),
      pct(r.recall_at_risk), pct(r.false_positive_rate), (r.reliable === "True" || r.reliable === true) ? "yes" : "too small"]),
    [1726, 600, 1100, 1000, 1000, 1000, 1400, 1200]),
  caption("Table 8.2: Test-year performance by province (groups under 20 municipalities, or under 5 per class, are too small to judge)."),
  figure("reports/figures/q8_fairness.png", "Figure 8.1: Recall, false-positive rate and accuracy by province and municipality type (test year).", 600),
  figure("reports/figures/q8_calibration.png", "Figure 8.2: Calibration of the locked model on the test year.", 330),
  P("**Limitations.** The model depends on last year's outcome (Question 6 ablation), so it cannot anticipate change. The financial " +
    "data is self-reported and sometimes implausible (for example cash coverage of −23.7 months); missing debtor and repairs data before " +
    "2020/2019 is recorded as zero; the grants extract appears truncated (only 182 municipalities), so grant dependency is unreliable; and " +
    "municipalities that fail to submit statements, the highest-risk group, have the least data. Results cover 2018–2024 only."),
  P("**Monitoring.** The model should be re-checked every year when the Auditor-General publishes municipal outcomes:"),
  B(`compare the 2025 forecast with the published outcomes and recompute macro-F1, recall and the false-positive rate overall and by province;`),
  B(`retrain on the newest year if macro-F1 falls below the lower confidence bound (${f3(ci8.macro_f1.ci95_low)}) or recall below ${f3(ci8.recall_at_risk.ci95_low)};`),
  B("check calibration and the share of municipalities that changed status, since a rise in changes means more misclassifications;"),
  B("run data-quality checks on each new extract (row limits, missing years recorded as zero, values outside the training range) before scoring."),
  P("**Do not use the model** to allocate funding or impose interventions automatically; to judge or penalise a municipality or its " +
    "officials; to predict deterioration in municipalities with a clean audit; for municipalities without audited figures, or after " +
    "boundary or accounting-standard changes (as with mSCOA) without re-validation; for years after 2025 without retraining; or when the " +
    "app warns that inputs are outside the range seen in training."),
  P("**Next steps that would make it an early-warning tool:** add in-year quarterly section 71 data, the number and type of audit " +
    "findings, senior-management vacancies and debt-collection trends, and model the probability of a **change** in status directly."),

  H2("8.2 Reproducible package"),
  P("The repository (private GitHub repository, shared with the lecturer on request) satisfies every item in the brief's checklist:"),
  table(["Requirement", "Where it is"], [
    ["README", "README.md: purpose, data source and licence, structure, setup, reproduction, dashboard launch"],
    ["Environment", "requirements.txt with pinned versions (Python 3.12; PyTorch CPU build)"],
    ["Fixed seeds", "Seed 42 for every split, model, search and bootstrap (src/models.py: SEED)"],
    ["Execution order", "python run_all.py runs all 11 steps in order; the README lists each script and the question it answers"],
    ["Source links", "README.md and docs/dataset_card.md link the Municipal Money site, API documentation and terms of use, and list each dataset used"],
    ["Data dictionary", "docs/data_dictionary.md (definitions, units, sources) and reports/data_dictionary.csv (types, missingness)"],
    ["Saved model / pipeline", "models/final_pipeline.joblib: preprocessing and the tuned model as one object"],
    ["User-interface code", "app/ (Streamlit), with sample inputs in app/samples and a smoke test in app/test_app.py"],
    ["Evidence bundle", "results/ (metric tables, paired McNemar predictions, forecasts), reports/figures/, docs/experiment_log.md, docs/dataset_card.md"],
    ["Licence", "Municipal Money terms allow reuse, so data/raw is included with attribution; no personal data is included"],
  ], [2200, 6826]),
  caption("Table 8.3: Reproducibility checklist."),
  P("**Reproduction test.** The repository was cloned into an empty folder and python run_all.py was run end to end. It completed " +
    "all 11 steps in 4.1 minutes on a laptop CPU without manual intervention. Every regenerated result file was identical to the committed " +
    "version: validation and cross-validation metrics, the Optuna result and one-time test evaluation, the ablations, McNemar's test, " +
    "all 1,679 municipality scores and forecasts, and the uncertainty and fairness tables. The only files that differed were saved model " +
    "objects and figure images (byte-level serialisation differences) and the dtype label of one column in the data audit " +
    "(pandas 3 reports text columns as str rather than object). There are no secrets, and every script finds its files relative to " +
    "the project folder, so the package runs on any machine."),

  H2("8.3 Presentation and contribution statement"),
  P("The 10–12 minute presentation follows the report: problem and stakeholder, data and leakage-safe split, models and evaluation, " +
    "optimisation, ablation and McNemar's test, a live dashboard demonstration (three valid municipalities and the invalid file from " +
    "Table 7.3, then a drill-down from the overview to a municipality profile), and the recommendation and limitations. Every member " +
    "presents the part they led and answers questions on the whole pipeline."),
  P("A one-page contribution statement (reports/IDA117V_Contribution_Statement.docx) lists each member's role and specific outputs, " +
    "with evidence from the repository's commit history, and is signed by all members."),
  P("**Declaration of AI assistance.** In line with the module's academic-integrity conditions, the team declares that an AI coding " +
    "assistant (Claude, by Anthropic) was used to help write and debug code (the Question 3 re-run, Questions 4–8 scripts and the " +
    "dashboard) and to draft parts of the Question 4–8 text. Commits produced with its help are labelled in the repository history. " +
    "The team reviewed, ran and checked all code and results and is responsible for the content of this report."),
);

const doc = new Document({
  creator: "IDA117V Group",
  title: "IDA117V Q4–Q8 report sections",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { size: 34, bold: true, color: "2E3546", font: FONT },
        paragraph: { spacing: { after: 200 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: "2E3546", font: FONT }, paragraph: { spacing: { before: 120, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: "3B6FEB", font: FONT }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: "IDA117V Group Project · Q4–Q8 · page ", size: 18, color: "777777" }),
      new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "777777" })] })] }) },
    children: content,
  }],
});

const out = path.join(ROOT, "reports", "IDA117V_Q4-Q8_Report_Sections.docx");
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(out, buf); console.log("Wrote", out); });
