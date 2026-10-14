"""
Municipal Audit Risk dashboard (IDA117V Q7).
Launch from the project root:  streamlit run app/app.py
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core
import nav
import theme as t
from views_explore import explore
from views_overview import overview
from views_profile import profile

st.set_page_config(page_title="Municipal Audit Risk", page_icon="📊", layout="wide")
t.inject_css()

OUTCOME_LABEL = {"at_risk": "At risk", "not_at_risk": "Not at risk"}
SAMPLES = core.ROOT / "app" / "samples"


# ----------------------------------------------------------------------------- risk check
def show_result(row: pd.DataFrame, title):
    prob, label = core.predict(row)
    prob, label = float(prob[0]), label[0]
    drivers = core.explain(row)
    color = t.RISK_COLORS[label]

    with st.container(key=f"card_result_{abs(hash(title))}"):
        t.card_title("Prediction", "Result", title)
        a, b = st.columns([1, 1.6], vertical_alignment="center")
        with a:
            st.plotly_chart(t.semi_gauge(prob * 100, "Probability of a poor audit", color),
                            width="stretch", config={"displayModeBar": False})
            st.html(f'<div style="text-align:center">{t.pill(OUTCOME_LABEL[label], color)}'
                    f'<div class="card-sub" style="margin-top:8px">{core.confidence_words(prob)} · '
                    f'decision threshold {core.THRESHOLD:.0%}</div></div>')
        with b:
            items = "".join(f"<li>{line}</li>" for line in core.plain_language(prob, label, drivers))
            st.html(f'<ul class="explain">{items}</ul>')
            if drivers:
                d = pd.DataFrame(drivers).iloc[::-1]
                fig = go.Figure(go.Bar(
                    x=d["contribution"], y=d["label"], orientation="h",
                    marker_color=[t.PINK if c > 0 else t.GREEN for c in d["contribution"]],
                    hovertemplate="%{y}<br>%{x:+.2f} log-odds<extra></extra>"))
                fig.update_xaxes(title="Push towards at risk (+) or not at risk (−)", zeroline=True,
                                 zerolinecolor=t.MUTED)
                st.plotly_chart(t.style_fig(fig, 60 + 34 * len(d), legend=False), width="stretch",
                                config={"displayModeBar": False})
        st.html('<div class="notice">A flag means "look closer and offer support", not "this municipality has '
                'failed". The model mostly relies on last year\'s audit, so it is weakest at spotting '
                'municipalities whose outcome is about to change.</div>')


def pick_municipality():
    latest = core.latest_rows()
    code = st.selectbox("Municipality", latest["demarcation.code"], index=None,
                        format_func=lambda c: f"{latest.set_index('demarcation.code').loc[c, 'Name']} ({c})",
                        placeholder="Type or choose a municipality…",
                        help="Uses the municipality's most recent audited figures (financial year 2024) "
                             "to forecast its 2025 audit.")
    if not code:
        st.info("Choose a municipality to see its forecast for the next audit, or open the Explorer to browse.")
        return
    row = latest[latest["demarcation.code"] == code].head(1)
    name = row["Name"].iloc[0]

    with st.container(key="card_profile"):
        t.card_title(name, f"({code})", f"{row['category'].iloc[0]} municipality · {row['province'].iloc[0]} · "
                     "audited 2024 indicators")
        cols = st.columns(5)
        for i, f in enumerate([f for f in core.NUMERIC_FEATURES if f != "total_expenditure"]):
            with cols[i % 5]:
                st.metric(core.FEATURE_INFO[f]["label"], core.fmt_value(f, row[f].iloc[0]),
                          help=core.FEATURE_INFO[f]["help"])
        hist = core.audit_history(code)
        chips = "".join(f'<span class="chip" style="background:{core.OPINION_COLORS.get(op, t.MUTED)}">'
                        f'{y}: {str(op).replace("_", " ")}</span>' for y, op in hist.items())
        st.html(f'<div class="card-sub" style="margin-top:6px">Audit opinions by year</div>{chips}')
        if st.button("Open full profile: history, trends and peers ›", type="primary"):
            nav.open_profile(code)
    _, _, warnings, _ = core.validate(row[["Name"] + core.FEATURES])
    for w in warnings:
        st.warning(w, icon="⚠️")
    st.write("")
    show_result(row, f"{name} — forecast for the {core.FORECAST_AUDIT_YEAR} audit")


def manual_entry():
    ref = core.reference_stats()
    info = core.FEATURE_INFO
    with st.form("manual"):
        st.caption("Enter one municipality's audited figures for year t. Defaults are typical (median) values "
                   "from the training years. Revenue and expenditure are in **rand millions**.")
        c = st.columns(3)
        rev = c[0].number_input("Total revenue (R million)", value=round(ref.loc["total_revenue", "median"] / 1e6, 1),
                                step=10.0, help=info["total_revenue"]["help"])
        exp = c[1].number_input("Total expenditure (R million)",
                                value=round(ref.loc["total_expenditure", "median"] / 1e6, 1),
                                step=10.0, help=info["total_expenditure"]["help"])
        prior = c[2].selectbox("Last year's audit opinion",
                               ["unqualified", "unqualified_emphasis_of_matter", "qualified", "adverse",
                                "disclaimer", "outstanding"],
                               format_func=lambda s: s.replace("_", " ").capitalize(),
                               help=info["prior_audit_outcome"]["help"])
        c = st.columns(3)
        cash = c[0].number_input("Cash coverage (months)", value=round(ref.loc["cash_coverage_ratio", "median"], 2),
                                 step=0.5, help=info["cash_coverage_ratio"]["help"])
        coll = c[1].number_input("Collection rate (%)", value=round(ref.loc["collection_rate", "median"] * 100, 1),
                                 step=1.0, help=info["collection_rate"]["help"])
        debt = c[2].number_input("Debtor days", value=round(ref.loc["debtor_days", "median"], 0), step=10.0,
                                 help=info["debtor_days"]["help"])
        c = st.columns(3)
        rm = c[0].number_input("Repairs & maintenance (% of expenditure)",
                               value=round(ref.loc["repairs_maintenance_ratio", "median"] * 100, 1), step=0.5,
                               help=info["repairs_maintenance_ratio"]["help"])
        irr = c[1].number_input("Irregular expenditure (% of expenditure)",
                                value=round(ref.loc["irregular_expenditure_ratio", "median"] * 100, 1), step=1.0,
                                help=info["irregular_expenditure_ratio"]["help"])
        grant = c[2].number_input("Grant dependency (% of revenue)",
                                  value=round(ref.loc["grant_dependency", "median"] * 100, 1), step=1.0,
                                  help=info["grant_dependency"]["help"])
        submitted = st.form_submit_button("Predict risk")
    if not submitted:
        return
    raw = pd.DataFrame([{
        "Name": "Entered municipality", "total_revenue": rev * 1e6, "total_expenditure": exp * 1e6,
        "cash_coverage_ratio": cash, "collection_rate": coll / 100, "debtor_days": debt,
        "repairs_maintenance_ratio": rm / 100, "irregular_expenditure_ratio": irr / 100,
        "grant_dependency": grant / 100, "prior_audit_outcome": prior,
    }])
    clean, errors, warnings, valid = core.validate(raw)
    for e in errors:
        st.error(e, icon="⛔")
    if errors:
        return
    for w in warnings:
        st.warning(w, icon="⚠️")
    show_result(clean[valid], "Manually entered figures")


def upload_csv():
    st.caption("Upload a CSV with one row per municipality. Required columns: **total_revenue**, "
               "**total_expenditure** (both in rand) and **prior_audit_outcome** (at_risk / not_at_risk or an AGSA "
               "opinion). Optional: Name and the ratio columns below; blanks are filled with typical values.")
    with st.expander("Column guide"):
        st.dataframe(pd.DataFrame([{"column": f, "meaning": core.FEATURE_INFO[f]["label"],
                                    "unit": core.FEATURE_INFO[f]["kind"].replace("pct", "fraction (0.95 = 95%)"),
                                    "description": core.FEATURE_INFO[f]["help"]} for f in core.FEATURES]),
                     hide_index=True, width="stretch")
    s1, s2 = st.columns(2)
    s1.download_button("Download sample: 3 valid cases", (SAMPLES / "valid_cases.csv").read_bytes(),
                       "valid_cases.csv", "text/csv")
    s2.download_button("Download sample: invalid case", (SAMPLES / "invalid_case.csv").read_bytes(),
                       "invalid_case.csv", "text/csv")
    file = st.file_uploader("CSV file", type=["csv"])
    if file is None:
        return
    try:
        raw = pd.read_csv(file, dtype=str)
    except Exception as exc:  # unreadable or non-CSV content
        st.error(f"Could not read the file as CSV: {exc}", icon="⛔")
        return
    clean, errors, warnings, valid = core.validate(raw)
    if clean is None:
        for e in errors:
            st.error(e, icon="⛔")
        return
    for e in errors:
        st.error(e, icon="⛔")
    for w in warnings:
        st.warning(w, icon="⚠️")
    good = clean[valid].copy()
    st.html(f'<div class="card-sub">{len(good)} of {len(clean)} rows are valid and were scored; '
            f'{len(clean) - len(good)} rows were skipped.</div>')
    if good.empty:
        return
    prob, label = core.predict(good)
    good["risk_probability"], good["predicted_class"] = prob, label
    good["main_driver"] = [core.explain(good.iloc[[i]])[0]["label"] for i in range(len(good))]
    name_col = good["Name"] if "Name" in good.columns else pd.Series([f"Row {i + 1}" for i in good.index], index=good.index)
    out = pd.DataFrame({"Municipality": name_col, "Risk": good["risk_probability"],
                        "Prediction": good["predicted_class"].map(OUTCOME_LABEL),
                        "Main driver": good["main_driver"]}).sort_values("Risk", ascending=False)
    with st.container(key="card_batch"):
        t.card_title("Batch", "Results", "Sorted from highest to lowest predicted risk")
        st.dataframe(out, hide_index=True, width="stretch", column_config={
            "Risk": st.column_config.ProgressColumn("Risk", format="percent", min_value=0, max_value=1)})
        st.download_button("Download results (CSV)", out.to_csv(index=False).encode(), "risk_predictions.csv",
                           "text/csv")
    if len(good) <= 5:
        for i in range(len(good)):
            st.write("")
            show_result(good.iloc[[i]], str(name_col.iloc[i]))


def risk_check():
    t.header("Risk", "Check", "Predict a municipality's next audit outcome with the locked final pipeline",
             "LR", "tuned<br>model")
    tab1, tab2, tab3 = st.tabs(["Pick a municipality", "Enter figures", "Upload CSV"])
    with tab1:
        pick_municipality()
    with tab2:
        manual_entry()
    with tab3:
        upload_csv()


# ----------------------------------------------------------------------------- evidence
def evidence():
    t.header("Model", "Evidence", "How the champion was chosen, tested and challenged (report Q4–Q6)",
             "6", "models<br>compared")
    q4, q5 = core.load_json("dashboard_q4.json"), core.load_json("q5_test_result.json")
    mc = core.load_json("q6_mcnemar.json")

    c1, c2 = st.columns(2)
    with c1, st.container(key="card_roc"):
        t.card_title("ROC", "Curves", "Validation year 2022 · positive class = at risk")
        fig = go.Figure()
        for name, curve in q4["roc"].items():
            auc = next(m["val_roc_auc"] for m in q4["models"] if m["model"] == name)
            fig.add_scatter(x=curve["fpr"], y=curve["tpr"], mode="lines", name=f"{name} ({auc:.3f})",
                            line=dict(color=t.MODEL_COLORS[name], width=2.5,
                                      dash="dash" if name.startswith("Baseline") else "solid"))
        fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=t.TRACK, dash="dot"), showlegend=False)
        fig.update_xaxes(title="False positive rate")
        fig.update_yaxes(title="True positive rate")
        st.plotly_chart(t.style_fig(fig, 470).update_layout(
            legend=dict(orientation="h", x=0, y=-0.22, yanchor="top", font=dict(size=10))),
            width="stretch", config={"displayModeBar": False})

    with c2, st.container(key="card_cv"):
        t.card_title("Cross-validation", "Stability", "Walk-forward CV inside 2018–2021 · mean ± SD macro-F1")
        mdl = pd.DataFrame(q4["models"])
        fig = go.Figure(go.Bar(
            x=mdl["model"], y=mdl["cv_macro_f1_mean"],
            error_y=dict(type="data", array=mdl["cv_macro_f1_std"], color=t.INK, thickness=1.5),
            marker_color=[t.MODEL_COLORS[x] for x in mdl["model"]],
            text=[f"{m:.2f}<br>±{s:.2f}" for m, s in zip(mdl["cv_macro_f1_mean"], mdl["cv_macro_f1_std"])],
            textposition="inside", insidetextanchor="start", textangle=0,
            textfont=dict(color="white", size=11)))
        fig.update_yaxes(range=[0, 1.1], title="Macro-F1")
        fig.update_xaxes(tickangle=-20)
        st.plotly_chart(t.style_fig(fig, 470, legend=False), width="stretch", config={"displayModeBar": False})

    st.write("")
    c3, c4 = st.columns([1, 1.25])
    with c3, st.container(key="card_cm"):
        t.card_title("Test-year", "Confusion matrix", f"Locked model on 2023 → 2024 (n = {q5['n_test']})")
        cm = np.array(q5["test_confusion"])
        fig = go.Figure(go.Heatmap(
            z=cm, x=["Predicted not at risk", "Predicted at risk"], y=["Actual not at risk", "Actual at risk"],
            colorscale=[[0, "#EEF1F6"], [1, t.BLUE]], showscale=False, text=cm, texttemplate="%{text}",
            textfont=dict(size=24, color=t.INK), hovertemplate="%{y} / %{x}: %{z}<extra></extra>"))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(t.style_fig(fig, 330, legend=False), width="stretch", config={"displayModeBar": False})

    with c4, st.container(key="card_abl"):
        t.card_title("Ablation", "Study", "Change one thing at a time · Δ vs the full tuned model (validation 2022)")
        abl = core.load_csv("q6_ablation.csv").iloc[1:]
        labels = [e.split(": ", 1)[1] for e in abl["experiment"]]
        fig = go.Figure()
        fig.add_bar(y=labels, x=abl["delta_val_macro_f1"], orientation="h", name="Δ Macro-F1", marker_color=t.PINK,
                    text=[f"{v:+.3f}" for v in abl["delta_val_macro_f1"]], textposition="outside")
        fig.add_bar(y=labels, x=abl["delta_val_roc_auc"], orientation="h", name="Δ ROC-AUC", marker_color=t.BLUE,
                    text=[f"{v:+.3f}" for v in abl["delta_val_roc_auc"]], textposition="outside")
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(range=[-0.36, 0.14], zeroline=True, zerolinecolor=t.INK)
        st.plotly_chart(t.style_fig(fig, 330), width="stretch", config={"displayModeBar": False})

    st.write("")
    c5, c6 = st.columns([1.1, 1])
    with c5, st.container(key="card_mcnemar"):
        t.card_title("McNemar's", "Test", f"Tuned LR vs {mc['comparator']} on the same {mc['n_test']} test municipalities")
        tb = mc["table"]
        st.html(f"""
<table class="mtable"><tr>
<td><b>{tb['both_correct']}</b><small>Both correct</small></td>
<td><b style="color:{t.PINK}">{tb['champion_only_correct']}</b><small>Champion only correct</small></td>
</tr><tr>
<td><b style="color:{t.PINK}">{tb['comparator_only_correct']}</b><small>Comparator only correct</small></td>
<td><b>{tb['both_wrong']}</b><small>Both wrong</small></td></tr></table>""")
        verdict = "Reject H₀" if mc["reject_H0"] else "Do not reject H₀"
        st.html(f'<div class="card-sub"><b>H₀:</b> {mc["H0"]}<br><b>H₁:</b> {mc["H1"]}<br>'
                f'{mc["test_version"]} · α = {mc["alpha"]} · <b>p = {mc["p_value"]:.4f}</b> → '
                f'{t.pill(verdict, t.GREEN if not mc["reject_H0"] else t.PINK)}</div>')

    with c6, st.container(key="card_tuning"):
        t.card_title("Champion", "Tuning", f"{q5['search_method']} · {q5['n_trials']} trials · {q5['scoring_rule']}")
        pp = pd.DataFrame(q5["pre_post"])
        r = st.columns(2)
        with r[0]:
            t.ring(pp.loc[0, "cv_macro_f1_mean"], "Before tuning", "CV macro-F1", "orange",
                   text=f"{pp.loc[0, 'cv_macro_f1_mean']:.3f}")
        with r[1]:
            t.ring(pp.loc[1, "cv_macro_f1_mean"], "After tuning", "CV macro-F1", "green",
                   text=f"{pp.loc[1, 'cv_macro_f1_mean']:.3f}")
        bp = q5["best_params"]
        st.html(f'<div class="card-sub" style="margin-top:10px">Chosen: C = {bp["C"]:.3f}, penalty = {bp["penalty"]}, '
                f'class weight = {bp["class_weight"]}, scaler = {bp["scaler"]}. The gain (+0.004) is smaller than the '
                f'fold-to-fold spread, so tuning mainly simplified the model (L1 removed 5 of 9 ratios).</div>')

    st.write("")
    with st.container(key="card_overfit"):
        t.card_title("Overfitting", "Check", "Training vs validation macro-F1 — a large gap means memorising")
        gap = core.load_csv("q4_overfitting_gap.csv")
        fig = go.Figure()
        fig.add_bar(x=gap["model"], y=gap["train_macro_f1"], name="Training (2018–2021)", marker_color=t.PURPLE)
        fig.add_bar(x=gap["model"], y=gap["val_macro_f1"], name="Validation (2022)", marker_color=t.TEAL)
        fig.update_yaxes(range=[0, 1.1], title="Macro-F1")
        st.plotly_chart(t.style_fig(fig, 300), width="stretch", config={"displayModeBar": False})


# ----------------------------------------------------------------------------- about
def about():
    t.header("About &", "Responsible use", "What this tool is for, how it was built and when not to use it",
             "i", "read<br>first")
    a, b = st.columns(2)
    with a, st.container(key="card_purpose"):
        t.card_title("Purpose", "")
        st.markdown(
            "- **Problem:** Auditor-General results arrive long after a financial year ends, so support for "
            "struggling municipalities usually follows the damage.\n"
            "- **Decision supported:** National Treasury and provincial treasuries ranking municipalities to "
            "prioritise financial-management support.\n"
            "- **Prediction:** whether a municipality's **next** audit (year t+1) is *at risk* (qualified, adverse, "
            "disclaimer or outstanding) using its audited figures and audit outcome for year t.\n"
            "- **Model:** tuned Logistic Regression (L1), chosen on validation macro-F1; fit on 2018–2022, "
            "tested once on 2023.")
    with b, st.container(key="card_limits"):
        t.card_title("Limitations &", "When not to use")
        st.markdown(
            "- The model leans heavily on **last year's audit outcome**; it rarely predicts a *change* in status, "
            "which is exactly when early warning matters most.\n"
            "- Its yes/no predictions are **the same as the rule \"repeat last year's outcome\"**. Its probabilities "
            "ranked risk better on the 2022 validation year (ROC-AUC 0.92 vs 0.89) but not on the 2023 test year "
            "(0.90 vs 0.90), so treat the ranking as a guide for ordering follow-up, not as precise risk.\n"
            "- Financial data is only as reliable as each municipality's submission; non-submitters have the "
            "least data yet are the highest risk.\n"
            "- **Do not use** to penalise municipalities, to allocate funding automatically, for years outside "
            "2018–2023 without re-validation, or after major boundary/accounting changes (e.g. mSCOA).\n"
            "- Province and municipal category act as proxies for rurality and poverty; check flagged lists for "
            "fair coverage before acting.\n"
            "- **Monitor** yearly: re-score when new audit outcomes are published and retrain if accuracy drops.")
    st.write("")
    c, d = st.columns(2)
    with c, st.container(key="card_data"):
        t.card_title("Data &", "Licence")
        st.markdown(
            "- **Source:** National Treasury, *Municipal Money* — municipaldata.treasury.gov.za (API).\n"
            "- **Licence:** free for commercial and non-commercial use under the Municipal Money Terms of Use.\n"
            "- **Coverage:** 257 municipalities, feature years 2018–2023 (1,434 municipality-years).\n"
            "- **Privacy (POPIA):** no personal data is used — the Municipal Officials dataset and contact "
            "fields were excluded.")
    with d, st.container(key="card_run"):
        t.card_title("How to", "Run")
        st.code("python -m venv .venv\n.venv\\Scripts\\activate\npip install -r requirements.txt\n"
                "streamlit run app/app.py", language="bash")
        st.caption("Loads models/final_pipeline.joblib. No credentials or personal data are needed or stored.")


pages = {
    "overview": st.Page(overview, title="Overview", icon=":material/dashboard:", url_path="overview", default=True),
    "explore": st.Page(explore, title="Explorer", icon=":material/travel_explore:", url_path="explore"),
    "risk": st.Page(risk_check, title="Risk check", icon=":material/query_stats:", url_path="risk-check"),
    "evidence": st.Page(evidence, title="Model evidence", icon=":material/insights:", url_path="evidence"),
    "about": st.Page(about, title="About & responsible use", icon=":material/info:", url_path="about"),
    "profile": st.Page(profile, title="Municipality profile", icon=":material/location_city:",
                       url_path="municipality", visibility="hidden"),
}
nav.PAGES.update(pages)
page = st.navigation(list(pages.values()), position="top")
nav.follow_pending()
page.run()
