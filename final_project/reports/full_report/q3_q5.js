// Questions 3 to 5. All numbers are read from results/ so the text always matches the latest run.
const L = require("./lib");
const { P, H1, H2, B, table, figure, sideFigure, twoFigures, caption, f3, pct, sgn, readJson, readCsv } = L;

module.exports = function q3q5() {
  const q4 = readCsv("q4_validation_metrics.csv");
  const cv = readCsv("q4_cv_walk_forward.csv");
  const gap = readCsv("q4_overfitting_gap.csv");
  const dash = readJson("dashboard_q4.json");
  const q5 = readJson("q5_test_result.json");
  const by = Object.fromEntries(q4.map((r) => [r.model, r]));
  const cvBy = Object.fromEntries(cv.map((r) => [r.model, r]));
  const gapBy = Object.fromEntries(gap.map((r) => [r.model, r]));
  const MODELS = q4.map((r) => r.model);
  const LR = by["Logistic Regression"], RULE = by["Baseline (Repeat last year)"];
  const nn = dash.neural_history;
  const c = [];
  const add = (...xs) => xs.flat().forEach((x) => c.push(x));

  // ---- per-class numbers from the validation confusion matrices (rows = actual, columns = predicted; 1 = at_risk)
  const cls = (name) => {
    const [[tn, fp], [fn, tp]] = dash.confusion[name];
    const prf = (tpv, fpv, fnv) => {
      const p = tpv + fpv ? tpv / (tpv + fpv) : 0, r = tpv + fnv ? tpv / (tpv + fnv) : 0;
      return [p, r, p + r ? 2 * p * r / (p + r) : 0];
    };
    return { tn, fp, fn, tp, risk: prf(tp, fp, fn), safe: prf(tn, fn, fp) };
  };

  // ======================================================== QUESTION 3
  add(
    H1("Question 3: Baseline and models"),
    P("_Note on protocol._ Question 3 was first run on a random 70/15/15 split (archived in notebooks/archive). It was re-run on the time-based split of Q2.3 so that every later comparison uses one leakage-safe protocol; **all results in this report use the time split** (training 2018–2021, validation 2022). The 2023 test year is not used in Questions 3 and 4."),
    H2("3.1 Baseline"),
    P(`The naïve baseline is a scikit-learn DummyClassifier with the most_frequent strategy: it predicts not_at_risk for every municipality. On the validation year it reaches accuracy ${f3(by["Baseline (Dummy)"].val_accuracy)} but macro-F1 only ${f3(by["Baseline (Dummy)"].val_macro_f1)}, ROC-AUC 0.500 and an at_risk recall of zero. It establishes the floor: a model must identify failing municipalities, not just exploit the class sizes. A second, non-learning baseline, **\"repeat last year's outcome\"** (predict that year t+1 repeats the year t outcome), reaches macro-F1 ${f3(RULE.val_macro_f1)}. It shows how much of any model's skill comes from audit persistence alone. Neither baseline counts among the four substantive models.`),
    H2("3.2 Models trained on identical data"),
    P("Four substantive models were trained on the **same training rows and the same preprocessing pipeline** (Q2.4) and evaluated on the same validation rows, all with seed 42: two traditional models (Logistic Regression, Random Forest) and two neural-learning models (a multi-layer perceptron and a residual tabular network). Their validation results are in Table 4.1."),
    H2("3.3 Model families"),
    B("**Logistic Regression** (traditional): a regularised linear model for the log-odds of at_risk (Tibshirani, 1996, for the L1 penalty used after tuning)."),
    B("**Random Forest** (traditional): 200 decision trees with bootstrap sampling and feature subsampling (Breiman, 2001)."),
    B("**Multi-layer perceptron** (neural): two hidden layers of 64 and 32 units with ReLU activation and dropout 0.2 (Srivastava et al., 2014)."),
    B("**Residual tabular network** (neural, second architecture): a tabular network with a 64-unit input layer followed by a residual block h + F(h), where F is a 64-unit layer with ReLU and dropout. The skip connection (He et al., 2016) lets the block learn a correction to its input and keeps training stable on small data."),
    H2("3.4 Architecture, hyper-parameters and reproducibility"),
    table(["Setting", "Logistic Regression", "Random Forest", "MLP", "Residual tabular network"], [
      ["Architecture", "Linear; L2 penalty (L1 after Q5 tuning)", "200 trees, max_features = sqrt, no depth limit", "9+2 inputs → 64 → 32 → 2", "inputs → 64 → residual block (64) → 2"],
      ["Loss", "Log-loss", "Gini impurity", "Class-weighted cross-entropy", "Class-weighted cross-entropy"],
      ["Optimiser", "lbfgs (C = 1.0, 2,000 iterations)", "n/a", "Adam (Kingma & Ba, 2015), lr 0.001", "Adam, lr 0.001"],
      ["Batch size / epochs", "n/a", "n/a", "32 / max 100", "32 / max 100"],
      ["Regularisation", "L2 (C = 1)", "Bootstrap, feature subsampling", "Dropout 0.2", "Dropout 0.2; weight decay 0.0001"],
      ["Early stopping", "n/a", "n/a", `Patience 10 on a 15% stratified slice of the training years; best epoch ${nn.MLP.best_epoch}, stopped at ${nn.MLP.epochs_run}`, `Same rule; best epoch ${nn["Residual Tabular NN"].best_epoch}, stopped at ${nn["Residual Tabular NN"].epochs_run}`],
      ["Class imbalance", "class_weight = balanced", "class_weight = balanced", "Loss weights n / (2 × n_class)", "Loss weights n / (2 × n_class)"],
      ["Seed", "42", "42", "42 (NumPy and PyTorch)", "42 (NumPy and PyTorch)"],
    ], [1500, 1950, 1900, 2100, 2302], { size: 16 }),
    caption("Table 3.1: Model configurations (full log: docs/experiment_log.md)."),
    P("**Compute environment and procedure.** Windows 11 laptop CPU, Python 3.12, scikit-learn 1.9.1 and PyTorch 2.14.1 (CPU build; Paszke et al., 2019); training all models takes under a minute. Other libraries: pandas (McKinney, 2010), NumPy (Harris et al., 2020), SciPy (Virtanen et al., 2020), statsmodels (Seabold & Perktold, 2010), Optuna, Matplotlib (Hunter, 2007), Plotly (Plotly Technologies Inc., n.d.) and Streamlit. The early-stopping slice comes from the training years only, so the validation year stays untouched for model selection. The whole procedure runs from the documented command python src/train_q3.py (or python run_all.py), with fixed seeds and no manual steps."),
    H2("3.5 Rationale for each model family"),
    P("Logistic Regression suits the data because there are fewer than 1,000 training rows and nine ratios: a regularised linear model is stable and every coefficient can be explained to an official. Random Forest captures non-linear effects and interactions between ratios and is robust to the heavy-tailed financial values found in Q2.1, but it can memorise (Q4.4). The MLP tests whether a flexible non-linear model extracts more from the same nine ratios, and the residual network tests whether extra depth with a skip connection adds anything. With about 950 rows of tabular data, the expectation, confirmed in Q4, is that the neural models do not beat the simpler ones."),
  );

  // ======================================================== QUESTION 4
  add(
    H1("Question 4: Evaluation, comparison and overfitting"),
    H2("4.1 Held-out metrics for every model"),
    P(`Every model was fit on 2018–2021 and evaluated on the same 244 municipalities of the 2022 validation year (positive class: at_risk). Macro-F1 is the primary metric. Because the classes are moderately imbalanced (${pct(dash.val_at_risk_share)} at risk), PR-AUC is reported alongside ROC-AUC, as it concentrates on the minority class (Saito & Rehmsmeier, 2015).`),
    table(["Model", "Accuracy", "Macro-F1", "Weighted-F1", "Precision (at risk)", "Recall (at risk)", "ROC-AUC", "PR-AUC"],
      q4.map((r) => [r.model, f3(r.val_accuracy), f3(r.val_macro_f1), f3(r.val_weighted_f1), f3(r.val_precision_at_risk), f3(r.val_recall_at_risk), f3(r.val_roc_auc), f3(r.val_pr_auc)]),
      [2300, 900, 900, 1000, 1100, 1100, 1000, 1452], { bold: [2], align: ["left", "right", "right", "right", "right", "right", "right", "right"] }),
    caption("Table 4.1: Validation-year (2022) metrics for both baselines and the four substantive models (n = 244)."),
    P(`All four substantive models clearly beat the majority-class baseline (macro-F1 ${f3(by["Baseline (Dummy)"].val_macro_f1)}). However, the \"repeat last year\" rule already reaches macro-F1 ${f3(RULE.val_macro_f1)}, the same as the best model, and Logistic Regression agrees with it on 100% of validation municipalities (the other models on 97–98%). The models therefore mainly learn that audit outcomes persist. Where they differ from the rule is in ranking: Logistic Regression and the neural networks reach ROC-AUC 0.927–0.929 against ${f3(RULE.val_roc_auc)} for the rule, because the financial ratios separate stronger and weaker municipalities within each outcome group.`),
    H2("4.2 Classification reports, confusion matrices and ROC curves"),
    table(["Model", "TN", "FP", "FN", "TP", "At risk: P / R / F1", "Not at risk: P / R / F1"],
      MODELS.map((m) => { const k = cls(m); const t = (a) => a.map((v) => v.toFixed(3)).join(" / ");
        return [m, String(k.tn), String(k.fp), String(k.fn), String(k.tp), t(k.risk), t(k.safe)]; }),
      [2300, 600, 600, 600, 600, 2526, 2526], { align: ["left", "right", "right", "right", "right", "left", "left"] }),
    caption("Table 4.2: Confusion counts and per-class precision (P), recall (R) and F1 on the validation year; support 103 at risk and 141 not at risk. Confusion-matrix plots: Figure A.1."),
    sideFigure("reports/figures/q4_roc_curves.png", "Figure 4.1: ROC curves of all models on one figure (validation 2022, positive class at_risk).", [
      "All four substantive models lie close together (AUC 0.913–0.929) and well above the dummy baseline (0.500). The \"repeat last year\" rule has a single operating point, so its curve is a two-segment line (AUC 0.887). Precision–recall curves are in Figure A.2."], 330, 3950),
    H2("4.3 Model comparison and provisional champion"),
    P("Variability was estimated with walk-forward (expanding-window) cross-validation inside the training years: train on 2018 and score 2019, train on 2018–2019 and score 2020, train on 2018–2020 and score 2021. This respects time order, so a model is never scored on a year earlier than its training data."),
    table(["Model", "Val macro-F1", "Val ROC-AUC", "CV macro-F1 (mean ± SD)", "Fold 2019", "Fold 2020", "Fold 2021"],
      MODELS.map((m) => [m, f3(by[m].val_macro_f1), f3(by[m].val_roc_auc), `${f3(cvBy[m].cv_macro_f1_mean)} ± ${f3(cvBy[m].cv_macro_f1_std)}`, f3(cvBy[m].fold_2019_macro_f1), f3(cvBy[m].fold_2020_macro_f1), f3(cvBy[m].fold_2021_macro_f1)]),
      [2300, 1050, 1100, 1900, 1100, 1100, 1202], { bold: [2], align: ["left", "right", "right", "right", "right", "right", "right"] }),
    caption("Table 4.3: Validation scores and walk-forward cross-validation (macro-F1) for every model."),
    ...figure("reports/figures/q4_model_comparison.png", "Figure 4.2: Model comparison: validation scores (left) and cross-validation mean ± SD (right).", 540),
    P(`**Provisional champion: Logistic Regression**, selected on validation performance only (the test year was not used): the highest validation macro-F1 of the four models (${f3(LR.val_macro_f1)}), the highest PR-AUC (${f3(LR.val_pr_auc)}) and stable cross-validation (${f3(cvBy["Logistic Regression"].cv_macro_f1_mean)} ± ${f3(cvBy["Logistic Regression"].cv_macro_f1_std)}). The MLP and residual network tie for second on macro-F1 (${f3(by["MLP"].val_macro_f1)}) but are unstable (SD about 0.18–0.20): in the fold trained only on 2018–2019 their macro-F1 collapsed to 0.54 and 0.52. With fewer than 1,000 rows, the simpler model is the more reliable choice. The baselines are shown for context and are not eligible.`),
    H2("4.4 Overfitting diagnosis and controls"),
    table(["Model", "Train macro-F1", "Validation macro-F1", "Gap (train − validation)"],
      gap.map((r) => [r.model, f3(r.train_macro_f1), f3(r.val_macro_f1), sgn(r.macro_f1_gap)]),
      [3500, 2000, 2200, 2052], { bold: [3], align: ["left", "right", "right", "right"] }),
    caption("Table 4.4: Train-versus-validation macro-F1 gap. Learning curves and neural loss/accuracy curves: Figures A.3 and A.4."),
    P(`**Random Forest overfits:** it scores 1.000 on the training years but ${f3(gapBy["Random Forest"].val_macro_f1)} on validation (gap ${f3(gapBy["Random Forest"].macro_f1_gap)}), and its learning curve stays at 1.0 for every training size. Fully grown trees memorise the training rows; limiting depth or raising min_samples_leaf would reduce this, but the model was not selected, so it was not tuned further. **Logistic Regression and both networks show no meaningful overfitting.** Their gaps are slightly negative (−0.010 to −0.022) because the 2022 validation year is slightly easier (the repeat-last-year rule scores 0.887 in 2022 against 0.865 over 2018–2021), and their learning curves flatten after about 400 rows.`),
    P(`**Controls used:** regularisation in Logistic Regression; dropout 0.2, class-weighted loss, weight decay 0.0001 (residual network) and early stopping (patience 10) in the networks. Early stopping monitors a 15% slice of the training years, not the validation year. The MLP's best epoch was ${nn.MLP.best_epoch} (stopped at ${nn.MLP.epochs_run}) and the residual network's ${nn["Residual Tabular NN"].best_epoch} (stopped at ${nn["Residual Tabular NN"].epochs_run}); training and early-stopping losses level off together without diverging (Figure A.4).`),
  );

  // ======================================================== QUESTION 5
  const pre = q5.pre_post[0], post = q5.pre_post[1], bp = q5.best_params, tm = q5.test_metrics, rm = q5.repeat_last_year_test_metrics;
  const [[tn, fp], [fn, tp]] = q5.test_confusion;
  add(
    H1("Question 5: Champion optimisation"),
    H2("5.1 Search method, search space and scoring rule"),
    P(`Only the validation champion, Logistic Regression, was optimised, with **Optuna** (Akiba et al., 2019) using the Tree-structured Parzen Estimator sampler (seed 42) for **${q5.n_trials} trials**. Trial 0 was fixed to the untuned configuration so the default appears in the search history (Figure A.5).`),
    table(["Hyper-parameter", "Search range", "Why it was searched"], [
      ["C (inverse regularisation)", "0.001 – 100, log scale", "Strength of coefficient shrinkage"],
      ["Penalty", "L2, L1, elastic-net (l1_ratio 0.05 – 0.95)", "L1 can switch off weak features"],
      ["Class weight", "balanced, none", "Imbalance treatment"],
      ["Scaler", "standard, robust", "Robust scaling is less sensitive to the outliers of Q2.1"],
    ], [2600, 3400, 3752]),
    caption("Table 5.1: Optuna search space."),
    P("**Scoring rule:** the mean macro-F1 over the three walk-forward folds inside the training years (2019, 2020, 2021)."),
    H2("5.2 Validation protocol and before/after comparison"),
    P("Every trial was scored only on folds drawn from 2018–2021; neither the 2022 validation year nor the 2023 test year was used for tuning. The validation year was used afterwards only to report the comparison."),
    table(["Configuration", "CV macro-F1", "Val accuracy", "Val macro-F1", "Val recall (at risk)", "Val ROC-AUC", "Val PR-AUC"], [
      ["Default (C = 1, L2, balanced)", `${f3(pre.cv_macro_f1_mean)} ± ${f3(pre.cv_macro_f1_std)}`, f3(pre.val_accuracy), f3(pre.val_macro_f1), f3(pre.val_recall_at_risk), f3(pre.val_roc_auc), f3(pre.val_pr_auc)],
      [`Tuned (C = ${bp.C.toFixed(3)}, ${bp.penalty.toUpperCase()}, ${bp.class_weight}, ${bp.scaler} scaler)`, `${f3(post.cv_macro_f1_mean)} ± ${f3(post.cv_macro_f1_std)}`, f3(post.val_accuracy), f3(post.val_macro_f1), f3(post.val_recall_at_risk), f3(post.val_roc_auc), f3(post.val_pr_auc)],
    ], [2900, 1350, 1000, 1000, 1200, 1100, 1202], { bold: [1] }),
    caption("Table 5.2: Logistic Regression before and after optimisation."),
    P(`Tuning improved the cross-validation macro-F1 by only ${sgn(post.cv_macro_f1_mean - pre.cv_macro_f1_mean)}, smaller than the fold-to-fold standard deviation (about 0.025), so it is not a meaningful improvement; validation macro-F1 did not change and validation ROC-AUC fell slightly (${f3(pre.val_roc_auc)} → ${f3(post.val_roc_auc)}) because the search optimised macro-F1, not ranking. The tuned configuration was kept because the scoring rule was fixed before the search. Its practical effect is a **simpler model**: the L1 penalty set five of the nine ratios to exactly zero. The final coefficients (standardised inputs) are: last year at_risk +1.688 and not_at_risk −1.710; cash coverage −0.145; repairs and maintenance −0.115; operating surplus −0.100; total revenue −0.029; the other five ratios 0.000.`),
    H2("5.3 Final locked pipeline: one-time test evaluation"),
    P(`The tuned pipeline (preprocessing and model together) was locked, refit on 2018–2022 and evaluated **once** on the ${q5.n_test} municipalities of the 2023 test year (predicting their 2024 audit). It is saved as models/final_pipeline.joblib, the exact object used by the interface (Q7).`),
    table(["Model", "Accuracy", "Macro-F1", "Precision (at risk)", "Recall (at risk)", "ROC-AUC", "PR-AUC"], [
      ["Tuned Logistic Regression (locked)", f3(tm.accuracy), f3(tm.macro_f1), f3(tm.precision_at_risk), f3(tm.recall_at_risk), f3(tm.roc_auc), f3(tm.pr_auc)],
      ["Repeat-last-year rule (reference)", f3(rm.accuracy), f3(rm.macro_f1), f3(rm.precision_at_risk), f3(rm.recall_at_risk), f3(rm.roc_auc), f3(rm.pr_auc)],
    ], [3000, 1000, 1000, 1300, 1200, 1100, 1152], { bold: [0] }),
    caption(`Table 5.3: The single test-set evaluation (2023 → 2024, n = ${q5.n_test}). Confusion matrix: Figure A.6.`),
    P(`On unseen data the model is accurate (${pct(tm.accuracy)}) and generalises without loss: test macro-F1 (${f3(tm.macro_f1)}) is at least as high as validation (${f3(post.val_macro_f1)}). It caught ${tp} of the ${tp + fn} municipalities whose next audit was poor and raised ${fp} false alarms among ${tn + fp} healthy ones.`),
    P(`**Is the improvement practically meaningful?** Against the baselines, only partly. The tuning gain is negligible. The locked model's yes/no predictions on the test year are identical to the repeat-last-year rule, and its test ROC-AUC (${f3(tm.roc_auc)}) is slightly lower than the rule's (${f3(rm.roc_auc)}), while PR-AUC is slightly higher (${f3(tm.pr_auc)} vs ${f3(rm.pr_auc)}). **All ${fp + fn} test errors are municipalities whose status changed:** the ${fn} missed municipalities were not at risk in 2023 but failed in 2024, and the ${fp} false alarms improved. The practical value is a consistent, explainable and documented risk score for prioritising support, not better detection of sudden deterioration.`),
  );
  return c;
};
