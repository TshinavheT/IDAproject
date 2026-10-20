// Appendices A to E and the reference list.
const L = require("./lib");
const { P, H1, H2, B, table, figure, twoFigures, caption, f3, pct, readCsv, readJson } = L;
const { Paragraph, TextRun } = L.docx;

const REFERENCES = [
  "Akiba, T., Sano, S., Yanase, T., Ohta, T. and Koyama, M. (2019) Optuna: A next-generation hyperparameter optimization framework. _Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining_, pp. 2623–2631.",
  "Auditor-General of South Africa (AGSA) (n.d.) _MFMA general reports on local government audit outcomes_. Available at: https://www.agsa.co.za",
  "Breiman, L. (2001) Random forests. _Machine Learning_, 45(1), pp. 5–32.",
  "Efron, B. (1979) Bootstrap methods: another look at the jackknife. _The Annals of Statistics_, 7(1), pp. 1–26.",
  "Harris, C.R. et al. (2020) Array programming with NumPy. _Nature_, 585, pp. 357–362.",
  "He, K., Zhang, X., Ren, S. and Sun, J. (2016) Deep residual learning for image recognition. _Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition_, pp. 770–778.",
  "Hunter, J.D. (2007) Matplotlib: a 2D graphics environment. _Computing in Science & Engineering_, 9(3), pp. 90–95.",
  "Kingma, D.P. and Ba, J. (2015) Adam: a method for stochastic optimization. _3rd International Conference on Learning Representations (ICLR)_.",
  "McKinney, W. (2010) Data structures for statistical computing in Python. _Proceedings of the 9th Python in Science Conference_, pp. 56–61.",
  "McNemar, Q. (1947) Note on the sampling error of the difference between correlated proportions or percentages. _Psychometrika_, 12(2), pp. 153–157.",
  "National Treasury (2014) _MFMA Circular No. 71: Uniform financial ratios and norms_. Pretoria: National Treasury.",
  "National Treasury (n.d.-a) _Municipal Money: Municipal Finance Data_. Available at: https://municipaldata.treasury.gov.za (now https://municipalmoney.gov.za).",
  "National Treasury (n.d.-b) _Municipal Finance Data API documentation_. Available at: https://municipaldata.treasury.gov.za/docs",
  "National Treasury (n.d.-c) _Municipal Money Terms of Use_. Available at: https://municipaldata.treasury.gov.za/terms",
  "Paszke, A. et al. (2019) PyTorch: an imperative style, high-performance deep learning library. _Advances in Neural Information Processing Systems_, 32.",
  "Pedregosa, F. et al. (2011) Scikit-learn: machine learning in Python. _Journal of Machine Learning Research_, 12, pp. 2825–2830.",
  "Plotly Technologies Inc. (n.d.) _Plotly Python graphing library_. Available at: https://plotly.com/python/",
  "Republic of South Africa (2003) _Local Government: Municipal Finance Management Act 56 of 2003_. Pretoria: Government Printer.",
  "Republic of South Africa (2013) _Protection of Personal Information Act 4 of 2013_. Pretoria: Government Printer.",
  "Saito, T. and Rehmsmeier, M. (2015) The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets. _PLOS ONE_, 10(3), e0118432.",
  "Seabold, S. and Perktold, J. (2010) statsmodels: econometric and statistical modeling with Python. _Proceedings of the 9th Python in Science Conference_.",
  "Srivastava, N., Hinton, G., Krizhevsky, A., Sutskever, I. and Salakhutdinov, R. (2014) Dropout: a simple way to prevent neural networks from overfitting. _Journal of Machine Learning Research_, 15, pp. 1929–1958.",
  "Streamlit Inc. (n.d.) _Streamlit_. Available at: https://streamlit.io",
  "Tibshirani, R. (1996) Regression shrinkage and selection via the lasso. _Journal of the Royal Statistical Society: Series B_, 58(1), pp. 267–288.",
  "Virtanen, P. et al. (2020) SciPy 1.0: fundamental algorithms for scientific computing in Python. _Nature Methods_, 17, pp. 261–272.",
];

function references() {
  return [
    H1("References", { pageBreakBefore: true }),
    ...REFERENCES.map((r) => new Paragraph({
      children: L.runs(r, { size: 19 }), spacing: { after: 70, line: 245 }, indent: { left: 360, hanging: 360 },
    })),
  ];
}

function appendices() {
  const fprov = readCsv("q8_fairness_province.csv");
  const ftype = readCsv("q8_fairness_type.csv");
  const ok = (r) => r.reliable === "True" || r.reliable === true;
  const c = [];
  const add = (...xs) => xs.flat().forEach((x) => c.push(x));
  add(
    H1("Appendices", { pageBreakBefore: true }),
    H2("Appendix A: Additional evaluation figures (Question 4)"),
    ...figure("reports/figures/q4_confusion_matrices.png", "Figure A.1: Confusion matrices for both baselines and all four models, validation year 2022 (n = 244).", 600),
    ...figure("reports/figures/q4_pr_curves.png", "Figure A.2: Precision–recall curves, validation 2022 (positive class at_risk).", 380),
    ...figure("reports/figures/q4_learning_curves.png", "Figure A.3: Learning curves: training vs validation macro-F1 as the training set grows.", 600),
    ...figure("reports/figures/q4_neural_training_curves.png", "Figure A.4: Neural networks: training vs early-stopping loss and accuracy per epoch (early-stopping slice = 15% of the training years).", 500),

    H2("Appendix B: Optimisation and test-year figures (Question 5)"),
    twoFigures(
      { rel: "reports/figures/q5_optimisation_history.png", text: "Figure A.5: Optuna optimisation history (each dot is a trial; the line is the best so far)." },
      { rel: "reports/figures/q5_test_confusion_matrix.png", text: "Figure A.6: Confusion matrix of the locked model on the 2023 test year." }, 300),

    H2("Appendix C: Fairness detail and calibration (Question 8)"),
    table(["Group", "n", "Actually at risk", "Flagged", "Accuracy", "Recall", "False-positive rate", "Judge?"],
      [...fprov.map((r) => [r.province, String(r.n), String(r.actual_at_risk), pct(r.flagged_share), pct(r.accuracy), pct(r.recall_at_risk), pct(r.false_positive_rate), ok(r) ? "yes" : "too small"]),
        ...ftype.map((r) => [r.category + " (type)", String(r.n), String(r.actual_at_risk), pct(r.flagged_share), pct(r.accuracy), pct(r.recall_at_risk), pct(r.false_positive_rate), ok(r) ? "yes" : "too small"])],
      [1900, 600, 1300, 1000, 1000, 1000, 1752, 1200], { align: ["left", "right", "right", "right", "right", "right", "right", "left"] }),
    caption("Table A.2: Test-year performance by province and municipality type (groups under 20 municipalities, or under 5 per class, are too small to judge)."),
    ...figure("reports/figures/q8_calibration.png", "Figure A.8: Calibration of the locked model on the test year (5 equal-size bins).", 330),

    H2("Appendix D: Dashboard (Question 7)"),
    table(["Click on", "Opens"], [
      ["Macro-F1 ring → Details", "Precision, recall and F1 for each class in the 2024 test year"],
      ["Recall ring → Details", "The at-risk municipalities that were caught and the 13 that were missed, with their before-and-after opinions"],
      ["Precision ring → Details", "The correct flags and the false alarms"],
      ["ROC-AUC ring → Details", "How predicted risk is spread for municipalities that did and did not fail"],
      ["Forecast gauges → See list", "The municipalities flagged for 2025, those at 80% or more, and those forecast to change status"],
      ["A point on the trend chart", "That audit year's opinion breakdown and at-risk share by province"],
      ["A top-10 bar or a table row", "That municipality's profile"],
      ["A province or category bar", "The Explorer, filtered accordingly"],
      ["A leaderboard bar", "That model's confusion matrix and cross-validation folds"],
    ], [3200, 6552]),
    caption("Table A.1: Drill-down interactions in the dashboard."),
    ...figure("reports/figures/app/app_overview_full.png", "Figure A.9: Overview page with test-year KPIs, the 2025 forecast, trend, highest-risk list and leaderboard.", 330),
    ...figure("reports/figures/app/app_explorer.png", "Figure A.10: Explorer with filters, clickable category charts, the municipality table and the biggest risk increases.", 330),
    ...figure("reports/figures/app/app_dialog_recall.png", "Figure A.11: Recall details: the 13 at-risk municipalities missed in the test year (every one had a clean audit the year before).", 480),
    ...figure("reports/figures/app/app_profile_trends.png", "Figure A.12: Profile of Emfuleni: financial-health trends against the national median and the peer comparison against Treasury norms.", 440),
    ...figure("reports/figures/app/app_risk_check_result.png", "Figure A.13: Risk check: forecast for Emfuleni with the predicted class, probability gauge, confidence, plain-language reasons and feature contributions.", 400),
    ...figure("reports/figures/app/app_invalid_input.png", "Figure A.7: Invalid manual input (total expenditure = 0) rejected with a clear error message.", 400),

    H2("Appendix E: Execution order"),
    P("python run_all.py runs these steps in order from the project root (about 4 minutes on a laptop CPU); seed 42 throughout.", { spacing: { after: 60 } }),
    table(["Step", "Script", "Question"], [
      ["(optional)", "src/build_modeling_dataset.py: download the cubes and build the modelling dataset (needs internet)", "Q2"],
      ["1", "src/audit_q21_v2.py: data audit → reports/data_dictionary.csv, reports/audit_report.txt", "Q2.1"],
      ["2", "src/visualize_q22_v2.py: five EDA figures", "Q2.2"],
      ["3", "src/split_q23_v2.py: time split (train 2018–2021, validation 2022, test 2023)", "Q2.3"],
      ["4", "src/pipeline_q24.py: preprocessing fit on training rows only", "Q2.4"],
      ["5", "src/train_q3.py: baselines and the four models", "Q3"],
      ["6", "src/evaluate_q4.py: metrics, ROC/PR, cross-validation, overfitting", "Q4"],
      ["7", "src/optimise_q5.py: Optuna tuning and the only use of the 2023 test year", "Q5"],
      ["8", "src/ablation_mcnemar_q6.py: ablations and McNemar's test", "Q6"],
      ["9", "src/forecast_next.py: score every municipality-year and forecast the 2025 audit", "Q7"],
      ["10", "src/fairness_q8.py: bootstrap intervals, calibration, fairness by province and type", "Q8"],
      ["11", "src/experiment_log.py: regenerate docs/experiment_log.md", "Q8"],
    ], [1100, 7300, 1352]),
    caption("Table A.3: Execution order."),
  );
  return c;
}

module.exports = { references, appendices };
