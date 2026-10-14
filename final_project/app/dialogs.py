"""
Drill-down dialogs opened from the overview: test-year metrics, forecast groups,
a single audit year, and a single model. Every municipality list is clickable and
opens that municipality's profile.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core
import nav
import theme as t

OUTCOME_LABEL = {"at_risk": "At risk", "not_at_risk": "Not at risk"}


def municipality_table(df, key, prob_col="risk_probability", extra=None, height=320):
    """Clickable list of municipalities; selecting a row opens its profile."""
    if df.empty:
        st.info("No municipalities in this group.")
        return
    cols = {"Municipality": df["Name"], "Code": df["demarcation.code"], "Province": df["province"],
            "Risk": df[prob_col]}
    for label, series in (extra or {}).items():
        cols[label] = series
    # Building from Series aligns (and re-sorts) on the index, so sort by risk explicitly.
    view = pd.DataFrame(cols).sort_values("Risk", ascending=False).reset_index(drop=True)
    event = st.dataframe(view, hide_index=True, width="stretch", height=height, on_select="rerun",
                         selection_mode="single-row", key=nav.chart_key(key), column_config={
                             "Risk": st.column_config.ProgressColumn("Risk", format="percent", min_value=0, max_value=1)})
    st.caption("Click a row to open the municipality's profile.")
    row = nav.selected_row(event)
    if row is not None:
        nav.open_profile(view.loc[row, "Code"])


def _test_rows():
    return core.year_rows(2024)


@st.dialog("Macro-F1 in depth", width="large")
def macro_f1_dialog():
    df = _test_rows()
    y, p = df["actual_next_outcome"], df["predicted_outcome"]
    rows = []
    for cls in ("at_risk", "not_at_risk"):
        tp = ((p == cls) & (y == cls)).sum()
        prec = tp / max((p == cls).sum(), 1)
        rec = tp / max((y == cls).sum(), 1)
        rows.append({"Class": OUTCOME_LABEL[cls], "Precision": prec, "Recall": rec,
                     "F1": 2 * prec * rec / max(prec + rec, 1e-9), "Municipalities": int((y == cls).sum())})
    st.markdown("Macro-F1 averages the F1 score of **both classes equally**, so a model cannot look good by only "
                "getting the larger group right. Scored on the 2024 audit (held-out test year).")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="%.3f") for c in ("Precision", "Recall", "F1")})
    st.metric("Macro-F1", f"{np.mean([r['F1'] for r in rows]):.3f}")


@st.dialog("Recall: at-risk municipalities caught and missed", width="large")
def recall_dialog():
    df = _test_rows()
    at = df[df["actual_next_outcome"] == "at_risk"]
    caught, missed = at[at["predicted_outcome"] == "at_risk"], at[at["predicted_outcome"] == "not_at_risk"]
    st.markdown(f"Of **{len(at)}** municipalities with a poor 2024 audit, the model flagged **{len(caught)}** "
                f"({len(caught) / len(at):.1%}) and missed **{len(missed)}**. "
                f"{(missed['prior_audit_outcome'] == 'not_at_risk').sum()} of the missed municipalities had a clean "
                f"audit the year before — the model does not see sudden deterioration coming.")
    tab1, tab2 = st.tabs([f"Missed ({len(missed)})", f"Caught ({len(caught)})"])
    with tab1:
        municipality_table(missed.sort_values("risk_probability", ascending=False), "dlg_missed",
                           extra={"2023 opinion": missed["prior_audit_opinion_raw"].str.replace("_", " "),
                                  "2024 opinion": missed["actual_next_opinion_raw"].str.replace("_", " ")})
    with tab2:
        municipality_table(caught.sort_values("risk_probability", ascending=False), "dlg_caught",
                           extra={"2024 opinion": caught["actual_next_opinion_raw"].str.replace("_", " ")})


@st.dialog("Precision: correct flags and false alarms", width="large")
def precision_dialog():
    df = _test_rows()
    flagged = df[df["predicted_outcome"] == "at_risk"]
    right = flagged[flagged["actual_next_outcome"] == "at_risk"]
    wrong = flagged[flagged["actual_next_outcome"] == "not_at_risk"]
    st.markdown(f"The model flagged **{len(flagged)}** municipalities for the 2024 audit; **{len(right)}** "
                f"({len(right) / len(flagged):.1%}) really did get a poor outcome. Of the **{len(wrong)}** false alarms, "
                f"{(wrong['prior_audit_outcome'] == 'at_risk').sum()} improved from a poor 2023 audit to a clean 2024 audit.")
    tab1, tab2 = st.tabs([f"False alarms ({len(wrong)})", f"Correct flags ({len(right)})"])
    with tab1:
        municipality_table(wrong.sort_values("risk_probability", ascending=False), "dlg_falsealarm",
                           extra={"2023 opinion": wrong["prior_audit_opinion_raw"].str.replace("_", " "),
                                  "2024 opinion": wrong["actual_next_opinion_raw"].str.replace("_", " ")})
    with tab2:
        municipality_table(right.sort_values("risk_probability", ascending=False), "dlg_rightflag",
                           extra={"2024 opinion": right["actual_next_opinion_raw"].str.replace("_", " ")})


@st.dialog("ROC-AUC: how well risk is ranked", width="large")
def roc_dialog():
    df = _test_rows()
    st.markdown("ROC-AUC is the chance that a randomly chosen municipality that **did** get a poor audit is given a "
                "higher risk score than one that did not. 1.0 is perfect ranking; 0.5 is guessing. The chart shows "
                "how the predicted risk is spread for each actual outcome in the 2024 audit.")
    fig = go.Figure()
    for cls, color in (("not_at_risk", t.GREEN), ("at_risk", t.PINK)):
        fig.add_histogram(x=df.loc[df["actual_next_outcome"] == cls, "risk_probability"] * 100,
                          name=f"Actually {OUTCOME_LABEL[cls].lower()}", marker_color=color, opacity=0.75,
                          xbins=dict(start=0, end=100, size=5))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title="Predicted risk (%)", range=[0, 100])
    fig.update_yaxes(title="Municipalities")
    st.plotly_chart(t.style_fig(fig, 320), width="stretch", config={"displayModeBar": False})
    st.caption("Two clear groups: the model is confident either way, which is why there are few 'close calls'. "
               "The overlap is the municipalities whose audit outcome changed.")


@st.dialog("2025 forecast group", width="large")
def forecast_group_dialog(group):
    fc = core.forecast_rows()
    if group == "flagged":
        df = fc[fc["predicted_outcome"] == "at_risk"]
        st.markdown(f"**{len(df)}** of {len(fc)} municipalities are forecast to receive a poor 2025 audit "
                    f"(probability ≥ 50%).")
    elif group == "high":
        df = fc[fc["risk_probability"] >= 0.8]
        st.markdown(f"**{len(df)}** municipalities have a forecast risk of 80% or more — the priority list for support.")
    else:
        df = fc[fc["predicted_outcome"] != fc["prior_audit_outcome"]]
        st.markdown(f"**{len(df)}** municipalities are forecast to **change** status in 2025 compared with their 2024 "
                    f"audit. These are the cases where the model adds information beyond last year's result.")
    municipality_table(df.sort_values("risk_probability", ascending=False), f"dlg_fc_{group}",
                       extra={"2024 opinion": df["prior_audit_opinion_raw"].str.replace("_", " "),
                              "Type": df["category"]})


@st.dialog("Audit year in depth", width="large")
def year_dialog(audit_year):
    df = core.year_rows(audit_year)
    forecast = audit_year == core.FORECAST_AUDIT_YEAR
    st.markdown(f"### {audit_year} audit {'(forecast)' if forecast else ''}")
    a, b = st.columns(2)
    with a:
        if forecast:
            counts = df["predicted_outcome"].map(OUTCOME_LABEL).value_counts()
            title = "Forecast outcome"
            colors = [t.RISK_COLORS["at_risk" if k == "At risk" else "not_at_risk"] for k in counts.index]
        else:
            counts = df["actual_next_opinion_raw"].value_counts()
            title = "Actual AGSA opinions"
            colors = [core.OPINION_COLORS.get(k, t.MUTED) for k in counts.index]
        fig = go.Figure(go.Pie(labels=[str(k).replace("_", " ") for k in counts.index], values=counts.values,
                               hole=0.6, marker=dict(colors=colors), sort=False, textinfo="percent"))
        fig.update_layout(title=dict(text=title, font=dict(size=13)))
        st.plotly_chart(t.style_fig(fig, 300), width="stretch", config={"displayModeBar": False})
    with b:
        target = "predicted_outcome" if forecast else "actual_next_outcome"
        prov = df.groupby("province")[target].apply(lambda s: (s == "at_risk").mean()).sort_values()
        fig = go.Figure(go.Bar(x=prov.values * 100, y=prov.index, orientation="h",
                               marker=dict(color=prov.values, colorscale=[[0, t.GREEN], [0.5, t.ORANGE], [1, t.PINK]]),
                               text=[f"{v:.0%}" for v in prov.values], textposition="outside"))
        fig.update_layout(title=dict(text="Share at risk by province", font=dict(size=13)))
        fig.update_xaxes(range=[0, 110], ticksuffix="%")
        st.plotly_chart(t.style_fig(fig, 300, legend=False), width="stretch", config={"displayModeBar": False})
    if st.button("Open this year in the Explorer", type="primary"):
        nav.open_explore(year=audit_year)


@st.dialog("Model in depth", width="large")
def model_dialog(name):
    q4 = core.load_json("dashboard_q4.json")
    m = next(x for x in q4["models"] if x["model"] == name)
    st.markdown(f"### {name}")
    c = st.columns(4)
    c[0].metric("Validation macro-F1", f"{m['val_macro_f1']:.3f}")
    c[1].metric("Validation ROC-AUC", f"{m['val_roc_auc']:.3f}")
    c[2].metric("Recall (at risk)", f"{m['val_recall_at_risk']:.3f}")
    c[3].metric("Train − validation gap", f"{m['train_macro_f1'] - m['val_macro_f1']:+.3f}")
    a, b = st.columns(2)
    with a:
        cm = np.array(q4["confusion"][name])
        fig = go.Figure(go.Heatmap(z=cm, x=["Pred. not at risk", "Pred. at risk"], y=["Not at risk", "At risk"],
                                   colorscale=[[0, "#EEF1F6"], [1, t.MODEL_COLORS[name]]], showscale=False,
                                   text=cm, texttemplate="%{text}", textfont=dict(size=20)))
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(title=dict(text="Confusion matrix (validation 2022)", font=dict(size=13)))
        st.plotly_chart(t.style_fig(fig, 280, legend=False), width="stretch", config={"displayModeBar": False})
    with b:
        folds = {k[5:9]: v for k, v in m.items() if k.startswith("fold_")}
        fig = go.Figure(go.Bar(x=list(folds), y=list(folds.values()), marker_color=t.MODEL_COLORS[name],
                               text=[f"{v:.2f}" for v in folds.values()], textposition="outside"))
        fig.update_yaxes(range=[0, 1.1], title="Macro-F1")
        fig.update_xaxes(title="Walk-forward fold (scored year)")
        fig.update_layout(title=dict(text="Cross-validation folds", font=dict(size=13)))
        st.plotly_chart(t.style_fig(fig, 280, legend=False), width="stretch", config={"displayModeBar": False})
