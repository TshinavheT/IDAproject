"""
Score every municipality-year with the locked final pipeline, including a forecast
of the next, not-yet-published audit.
Run from the project root:  python src/forecast_next.py

Rebuilds features from the cached raw cubes in data/raw (no API calls) with the
same engineer_features() used to build modeling_dataset.csv, and checks that the
rebuilt 2018-2023 values match it before scoring anything.

Each row is labelled by how the model relates to it:
  fitted    feature years 2018-2022 (the final model was fit on these: in-sample)
  test      feature year 2023 -> 2024 audit (the one-time held-out test, Q5.3)
  forecast  feature year 2024 -> 2025 audit (outcome not yet known)

Saves results/municipality_scores.csv (used by the dashboard's drill-downs).
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from build_modeling_dataset import AT_RISK, NOT_AT_RISK, engineer_features
from pipeline_q24 import CATEGORICAL_FEATURES, NUMERIC_FEATURES

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW = PROJECT_ROOT / "data" / "raw"
PROCESSED = PROJECT_ROOT / "data" / "processed"
RESULTS = PROJECT_ROOT / "results"
IDX = ["demarcation.code", "financial_year_end.year"]

METROS = {"BUF": "Eastern Cape", "NMA": "Eastern Cape", "MAN": "Free State", "EKU": "Gauteng",
          "JHB": "Gauteng", "TSH": "Gauteng", "ETH": "KwaZulu-Natal", "CPT": "Western Cape"}
PREFIXES = {"EC": "Eastern Cape", "FS": "Free State", "GT": "Gauteng", "KZN": "KwaZulu-Natal",
            "LIM": "Limpopo", "MP": "Mpumalanga", "NW": "North West", "NC": "Northern Cape",
            "WC": "Western Cape"}
DISTRICTS = {"Western Cape": [1, 2, 3, 4, 5], "Northern Cape": [6, 7, 8, 9, 45],
             "Eastern Cape": [10, 12, 13, 14, 15, 44], "Free State": [16, 18, 19, 20],
             "KwaZulu-Natal": [21, 22, 23, 24, 25, 26, 27, 28, 29, 43], "Mpumalanga": [30, 31, 32],
             "Limpopo": [33, 34, 35, 36, 47], "North West": [37, 38, 39, 40], "Gauteng": [42, 48]}
DISTRICT_PROVINCE = {n: prov for prov, nums in DISTRICTS.items() for n in nums}


def province_and_category(code):
    if code in METROS:
        return METROS[code], "Metro"
    if code.startswith("DC") and code[2:].isdigit():
        return DISTRICT_PROVINCE.get(int(code[2:]), "Unknown"), "District"
    for prefix in sorted(PREFIXES, key=len, reverse=True):
        if code.startswith(prefix):
            return PREFIXES[prefix], "Local"
    return "Unknown", "Unknown"


def outcome(code):
    return "at_risk" if code in AT_RISK else ("not_at_risk" if code in NOT_AT_RISK else None)


def main():
    raw = {name: pd.read_csv(RAW / f"{name}_audited_all.csv", low_memory=False)
           for name in ("incexp", "finpos", "debtor", "repmaint", "uifwexp", "grants")}
    features = engineer_features(raw["incexp"], raw["finpos"], raw["debtor"],
                                 raw["repmaint"], raw["uifwexp"], raw["grants"])
    for c in NUMERIC_FEATURES:  # ratios use pd.NA for divide-by-zero; make them plain floats
        features[c] = pd.to_numeric(features[c], errors="coerce").astype(float)

    # Consistency check: rebuilt features must reproduce the modelling dataset.
    model_df = pd.read_csv(PROCESSED / "modeling_dataset.csv", low_memory=False)
    check = model_df[IDX + NUMERIC_FEATURES].merge(features, on=IDX, suffixes=("", "_rebuilt"))
    worst = max(np.nanmax(np.abs(check[c] - check[f"{c}_rebuilt"]) / np.maximum(np.abs(check[c]), 1))
                for c in NUMERIC_FEATURES)
    print(f"Rebuilt features matched for {len(check)}/{len(model_df)} rows; worst relative difference = {worst:.2e}")
    if len(check) != len(model_df) or worst > 1e-6:
        raise RuntimeError("Rebuilt features do not match modeling_dataset.csv; refusing to score.")

    audit = pd.read_csv(RAW / "audit_opinion_facts.csv").rename(
        columns={"Demarcation Code": "demarcation.code", "Year End": "financial_year_end.year"})
    audit["outcome"] = audit["Code"].map(outcome)
    audit = audit.dropna(subset=["outcome"])
    names = audit.sort_values("financial_year_end.year").groupby("demarcation.code")["Name"].last()

    prior = audit[IDX + ["outcome", "Code"]].rename(
        columns={"outcome": "prior_audit_outcome", "Code": "prior_audit_opinion_raw"})
    nxt = audit[IDX + ["outcome", "Code"]].rename(
        columns={"outcome": "actual_next_outcome", "Code": "actual_next_opinion_raw"})
    nxt["financial_year_end.year"] -= 1

    scores = features.merge(prior, on=IDX, how="inner").merge(nxt, on=IDX, how="left")
    scores = scores[scores["financial_year_end.year"].between(2018, 2024)].copy()
    scores["Name"] = scores["demarcation.code"].map(names)
    geo = scores["demarcation.code"].map(province_and_category)
    scores["province"] = [g[0] for g in geo]
    scores["category"] = [g[1] for g in geo]
    scores["audit_year"] = scores["financial_year_end.year"] + 1
    scores["split"] = np.select(
        [scores["financial_year_end.year"] <= 2022, scores["financial_year_end.year"] == 2023],
        ["fitted", "test"], "forecast")

    pipe = joblib.load(PROJECT_ROOT / "models" / "final_pipeline.joblib")
    scores["risk_probability"] = pipe.predict_proba(scores[NUMERIC_FEATURES + CATEGORICAL_FEATURES])[:, 1]
    scores["predicted_outcome"] = np.where(scores["risk_probability"] >= 0.5, "at_risk", "not_at_risk")

    test = scores[scores["split"] == "test"]
    test_preds = pd.read_csv(RESULTS / "q5_test_predictions.csv")
    merged = test.merge(test_preds, on="demarcation.code")
    assert np.allclose(merged["risk_probability"], merged["champion_prob"]), "test-year scores differ from Q5"
    print(f"Test-year probabilities match Q5 for {len(merged)} municipalities")

    scores = scores.sort_values(["demarcation.code", "financial_year_end.year"])
    scores.to_csv(RESULTS / "municipality_scores.csv", index=False)
    fc = scores[scores["split"] == "forecast"]
    print(f"\nRows by split: {scores['split'].value_counts().to_dict()}")
    print(f"Forecast for the 2025 audit: {len(fc)} municipalities, "
          f"{(fc['predicted_outcome'] == 'at_risk').sum()} flagged at risk "
          f"(mean risk {fc['risk_probability'].mean():.1%})")
    print("Unknown provinces:", sorted(scores.loc[scores["province"] == "Unknown", "demarcation.code"].unique()))


if __name__ == "__main__":
    main()
