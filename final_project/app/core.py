"""
Prediction logic for the dashboard: loads the locked Q5 pipeline, validates input,
predicts and explains. Nothing here retrains a model; the app only ever uses
models/final_pipeline.joblib (tuned Logistic Regression, fit on 2018-2022).
"""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pipeline_q24 import CATEGORICAL_FEATURES, NUMERIC_FEATURES  # noqa: E402

PIPELINE_PATH = ROOT / "models" / "final_pipeline.joblib"
RESULTS = ROOT / "results"
DATASET = ROOT / "data" / "processed" / "modeling_dataset.csv"
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
THRESHOLD = 0.5

FEATURE_INFO = {
    "total_revenue": dict(label="Total revenue", kind="rand",
                          help="Total operating revenue for the financial year (audited actual)."),
    "total_expenditure": dict(label="Total expenditure", kind="rand",
                              help="Total operating expenditure for the financial year (audited actual)."),
    "operating_surplus": dict(label="Operating surplus / deficit", kind="rand",
                              help="Revenue minus expenditure. Negative means an operating deficit. "
                                   "Calculated automatically from revenue and expenditure."),
    "cash_coverage_ratio": dict(label="Cash coverage", kind="months",
                                help="Cash and cash equivalents divided by average monthly expenditure. "
                                     "National Treasury's MFMA Circular 71 norm is 1–3 months."),
    "collection_rate": dict(label="Collection rate", kind="pct",
                            help="(Billed revenue − bad debts) ÷ billed revenue. Circular 71 norm: 95%."),
    "debtor_days": dict(label="Debtor days", kind="days",
                        help="Total debtors ÷ (revenue ÷ 365): how many days of revenue are still owed."),
    "repairs_maintenance_ratio": dict(label="Repairs & maintenance spend", kind="pct",
                                      help="Repairs and maintenance spending as a share of total expenditure."),
    "irregular_expenditure_ratio": dict(label="Irregular expenditure", kind="pct",
                                        help="Unauthorised, irregular, fruitless and wasteful expenditure "
                                             "as a share of total expenditure. The norm is 0%."),
    "grant_dependency": dict(label="Grant dependency", kind="pct",
                             help="Grants received as a share of total revenue."),
    "prior_audit_outcome": dict(label="Last year's audit outcome", kind="category",
                                help="The Auditor-General outcome for the same financial year t. "
                                     "at_risk = qualified, adverse, disclaimer or outstanding; "
                                     "not_at_risk = unqualified (with or without findings)."),
}
OPINION_TO_OUTCOME = {
    "unqualified": "not_at_risk", "unqualified_emphasis_of_matter": "not_at_risk",
    "qualified": "at_risk", "adverse": "at_risk", "disclaimer": "at_risk", "outstanding": "at_risk",
    "at_risk": "at_risk", "not_at_risk": "not_at_risk",
}
OPINION_COLORS = {
    "unqualified": "#22B07D", "unqualified_emphasis_of_matter": "#20C3B0", "qualified": "#F5A524",
    "adverse": "#F0507A", "disclaimer": "#E83E6C", "outstanding": "#8B5CF6",
}
REQUIRED = ["total_revenue", "total_expenditure", "prior_audit_outcome"]


def fmt_value(feature, value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "missing"
    kind = FEATURE_INFO[feature]["kind"]
    if kind == "rand":
        sign = "−" if value < 0 else ""
        v = abs(value)
        return f"{sign}R{v / 1e9:.2f} bn" if v >= 1e9 else f"{sign}R{v / 1e6:.1f} m"
    if kind == "months":
        return f"{value:.1f} months"
    if kind == "pct":
        return f"{value * 100:.1f}%"
    if kind == "days":
        return f"{value:.0f} days"
    return str(value).replace("_", " ")


@st.cache_resource
def load_pipeline():
    return joblib.load(PIPELINE_PATH)


@st.cache_data
def load_json(name):
    return json.loads((RESULTS / name).read_text())


@st.cache_data
def load_csv(name):
    return pd.read_csv(RESULTS / name)


@st.cache_data
def load_dataset():
    return pd.read_csv(DATASET, low_memory=False)


@st.cache_data
def reference_stats():
    """Typical values and plausible ranges from the years the final model was fit on (2018-2022)."""
    df = load_dataset()
    fit = df[df["financial_year_end.year"] <= 2022]
    return pd.DataFrame({
        "median": fit[NUMERIC_FEATURES].median(),
        "p01": fit[NUMERIC_FEATURES].quantile(0.01),
        "p99": fit[NUMERIC_FEATURES].quantile(0.99),
    })


SPLIT_LABEL = {"fitted": "Fitted years (in-sample)", "test": "Held-out test", "forecast": "Forecast"}
FORECAST_AUDIT_YEAR = 2025


@st.cache_data
def load_scores():
    """Every municipality-year scored by the locked model (src/forecast_next.py)."""
    return pd.read_csv(RESULTS / "municipality_scores.csv", low_memory=False)


def year_rows(audit_year):
    s = load_scores()
    return s[s["audit_year"] == audit_year].sort_values("Name").reset_index(drop=True)


def forecast_rows():
    return year_rows(FORECAST_AUDIT_YEAR)


def latest_rows():
    """Most recent feature year per municipality (2024 -> forecasts the 2025 audit)."""
    return forecast_rows()


def municipality(code):
    s = load_scores()
    return s[s["demarcation.code"] == code].sort_values("audit_year").reset_index(drop=True)


def audit_history(code):
    """{year: AGSA opinion} for every year with a published opinion."""
    rows = municipality(code)
    hist = {int(r["financial_year_end.year"]): r["prior_audit_opinion_raw"] for _, r in rows.iterrows()}
    for _, r in rows.iterrows():
        if isinstance(r["actual_next_opinion_raw"], str):
            hist[int(r["audit_year"])] = r["actual_next_opinion_raw"]
    return dict(sorted(hist.items()))


def opinion_streak(history):
    """(outcome, years) for the run of identical outcomes ending at the latest opinion."""
    if not history:
        return None, 0
    outcomes = [OPINION_TO_OUTCOME.get(op) for _, op in sorted(history.items())]
    last, n = outcomes[-1], 0
    for o in reversed(outcomes):
        if o != last:
            break
        n += 1
    return last, n


def validate(raw: pd.DataFrame):
    """Check user input. Returns (clean frame, errors, warnings, valid-row mask)."""
    errors, warnings = [], []
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    missing_cols = [c for c in REQUIRED if c not in df.columns]
    if missing_cols:
        return None, [f"Missing required column(s): {', '.join(missing_cols)}. "
                      f"Expected columns: {', '.join(FEATURES)}."], [], None
    if len(df) == 0:
        return None, ["The file has no data rows."], [], None
    if len(df) > 500:
        return None, [f"The file has {len(df)} rows; the limit is 500 per upload."], [], None

    for col in NUMERIC_FEATURES:
        if col not in df.columns:
            df[col] = np.nan
    valid = pd.Series(True, index=df.index)
    ref = reference_stats()
    row_label = df["Name"].astype(str) if "Name" in df.columns else pd.Series(
        [f"Row {i + 1}" for i in range(len(df))], index=df.index)

    for col in NUMERIC_FEATURES:
        original = df[col]
        blank = original.isna() | (original.astype(str).str.strip() == "")
        numeric = pd.to_numeric(original.astype(str).str.replace(",", "").str.replace(" ", ""), errors="coerce")
        bad = ~blank & numeric.isna()
        for i in df.index[bad]:
            errors.append(f"{row_label[i]}: '{original[i]}' is not a number for {FEATURE_INFO[col]['label']}.")
        valid &= ~bad
        df[col] = numeric.where(~blank)

    for col in ("total_revenue", "total_expenditure"):
        nonpos = df[col].notna() & (df[col] <= 0)
        blank = df[col].isna()
        for i in df.index[blank & valid]:
            errors.append(f"{row_label[i]}: {FEATURE_INFO[col]['label']} is required.")
        for i in df.index[nonpos]:
            errors.append(f"{row_label[i]}: {FEATURE_INFO[col]['label']} must be greater than zero (in rand).")
        valid &= ~(nonpos | blank)

    computed = df["total_revenue"] - df["total_expenditure"]
    given = df["operating_surplus"]
    mismatch = given.notna() & computed.notna() & ((given - computed).abs() > 0.01 * computed.abs().clip(lower=1e6))
    for i in df.index[mismatch & valid]:
        warnings.append(f"{row_label[i]}: operating surplus did not equal revenue − expenditure; recalculated.")
    df["operating_surplus"] = computed

    outcome = df["prior_audit_outcome"].astype(str).str.strip().str.lower().str.replace(" ", "_")
    mapped = outcome.map(OPINION_TO_OUTCOME)
    for i in df.index[mapped.isna()]:
        errors.append(f"{row_label[i]}: last year's audit outcome '{df['prior_audit_outcome'][i]}' is not recognised. "
                      f"Use at_risk / not_at_risk or an AGSA opinion (unqualified, qualified, adverse, "
                      f"disclaimer, outstanding).")
    valid &= mapped.notna()
    df["prior_audit_outcome"] = mapped

    for col in NUMERIC_FEATURES:
        if col in ("total_revenue", "total_expenditure", "operating_surplus"):
            continue
        blank = df[col].isna() & valid
        for i in df.index[blank]:
            warnings.append(f"{row_label[i]}: {FEATURE_INFO[col]['label']} is blank; the typical value "
                            f"({fmt_value(col, ref.loc[col, 'median'])}) will be used.")
        lo, hi = ref.loc[col, "p01"], ref.loc[col, "p99"]
        unusual = df[col].notna() & ((df[col] < lo) | (df[col] > hi)) & valid
        for i in df.index[unusual]:
            warnings.append(f"{row_label[i]}: {FEATURE_INFO[col]['label']} = {fmt_value(col, df[col][i])} is outside "
                            f"the range seen in 98% of training data ({fmt_value(col, lo)} to {fmt_value(col, hi)}); "
                            f"treat this prediction with extra caution.")
    return df, errors, warnings, valid


def predict(df: pd.DataFrame):
    pipe = load_pipeline()
    prob = pipe.predict_proba(df[FEATURES])[:, 1]
    return prob, np.where(prob >= THRESHOLD, "at_risk", "not_at_risk")


def explain(row: pd.DataFrame):
    """Per-feature contributions to the log-odds of at_risk (coefficient × transformed value)."""
    pipe = load_pipeline()
    pre, clf = pipe.named_steps["preprocess"], pipe.named_steps["model"]
    z = np.asarray(pre.transform(row[FEATURES]))[0]
    names = pre.get_feature_names_out()
    contrib = {}
    for name, value, coef in zip(names, z, clf.coef_[0]):
        feature = name.split("__", 1)[1]
        if feature.startswith("prior_audit_outcome"):
            feature = "prior_audit_outcome"
        contrib[feature] = contrib.get(feature, 0.0) + value * coef
    ref = reference_stats()
    out = []
    for feature, c in contrib.items():
        if abs(c) < 1e-6:
            continue
        typical = "" if feature == "prior_audit_outcome" else fmt_value(feature, ref.loc[feature, "median"])
        out.append(dict(feature=feature, label=FEATURE_INFO[feature]["label"],
                        value=fmt_value(feature, row[feature].iloc[0]), typical=typical, contribution=c))
    return sorted(out, key=lambda d: -abs(d["contribution"]))


def confidence_words(prob):
    margin = abs(prob - THRESHOLD)
    if margin >= 0.35:
        return "High confidence"
    if margin >= 0.15:
        return "Moderate confidence"
    return "Low confidence — close call"


def plain_language(prob, label, drivers):
    risk = "at risk of a poor audit outcome (qualified, adverse, disclaimer or outstanding)" \
        if label == "at_risk" else "likely to receive an unqualified audit opinion"
    lines = [f"The model estimates a <b>{prob:.0%}</b> chance that this municipality's next audit is poor, "
             f"so it is flagged as <b>{risk}</b>."]
    for d in drivers[:3]:
        direction = '<span class="up">raises</span>' if d["contribution"] > 0 else '<span class="down">lowers</span>'
        if d["feature"] == "prior_audit_outcome":
            lines.append(f"Last year's audit outcome (<b>{d['value']}</b>) {direction} the risk the most — "
                         f"audit results tend to repeat from year to year.")
        else:
            lines.append(f"{d['label']} of <b>{d['value']}</b> (typical: {d['typical']}) {direction} the risk.")
    return lines
