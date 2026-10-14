"""
Overview page: test-year model KPIs and the forecast for the next audit. Every
ring, gauge and chart drills down into a dialog, the explorer or a profile.
"""

import plotly.graph_objects as go
import streamlit as st

import core
import dialogs
import nav
import theme as t


def details_button(key, label="Details ›"):
    return st.button(label, key=key, type="tertiary", width="stretch")


def overview():
    q5 = core.load_json("q5_test_result.json")
    m = q5["test_metrics"]
    fc = core.forecast_rows()
    n = len(fc)
    flagged = int((fc["predicted_outcome"] == "at_risk").sum())
    high = int((fc["risk_probability"] >= 0.8).sum())
    changing = int((fc["predicted_outcome"] != fc["prior_audit_outcome"]).sum())

    t.header("Audit Risk", "Dashboard",
             "Which South African municipalities are likely to fail their next Auditor-General audit? "
             "Tuned Logistic Regression · National Treasury Municipal Money data",
             n, f"{core.FORECAST_AUDIT_YEAR}<br>forecasts")

    # ------------------------------------------------------------- model KPIs (test year)
    with st.container(key="card_kpis"):
        left, right = st.columns([1, 3.2], vertical_alignment="center")
        with left:
            t.card_title("Model", "KPIs", "Locked model, scored once on the unseen 2024 audit (test year)")
            t.stat(f"{m['accuracy']:.1%}", "Accuracy", t.BLUE, "✓")
            t.stat(f"{m['macro_f1']:.3f}", "Macro-F1 (primary metric)", t.PINK, "★")
        with right:
            cols = st.columns(4)
            rings = [(m["macro_f1"], "Macro-F1", "Balance of both classes", "pink", dialogs.macro_f1_dialog),
                     (m["recall_at_risk"], "Recall (at risk)", "Failing municipalities caught", "orange",
                      dialogs.recall_dialog),
                     (m["precision_at_risk"], "Precision (at risk)", "Flags that were right", "green",
                      dialogs.precision_dialog),
                     (m["roc_auc"], "ROC-AUC", "How well risk is ranked", "blue", dialogs.roc_dialog)]
            for col, (value, label, note, color, dialog) in zip(cols, rings):
                with col:
                    t.ring(value, label, note, color)
                    if details_button(f"ring_{label}"):
                        dialog()

    st.write("")
    c1, c2 = st.columns([1.05, 1])
    # ------------------------------------------------------------- forecast outlook
    with c1, st.container(key="card_outlook"):
        t.card_title(f"{core.FORECAST_AUDIT_YEAR}", "Forecast",
                     f"Audited {core.FORECAST_AUDIT_YEAR - 1} figures → predicted {core.FORECAST_AUDIT_YEAR} audit outcomes")
        g = st.columns(3)
        gauges = [(flagged / n * 100, "Flagged at risk", t.PINK, "flagged", f"{flagged} municipalities"),
                  (high / n * 100, "High risk (≥ 80%)", t.ORANGE, "high", f"{high} municipalities"),
                  (changing / n * 100, "Changing status", t.TEAL, "changing",
                   f"{changing} municipalities" if changing else "none — every forecast repeats the 2024 outcome")]
        for col, (value, title, color, group, caption) in zip(g, gauges):
            with col:
                st.plotly_chart(t.semi_gauge(value, title, color), width="stretch", config={"displayModeBar": False})
                st.html(f'<div class="card-sub" style="text-align:center;margin-top:-8px">{caption}</div>')
                if details_button(f"gauge_{group}", "See list ›"):
                    dialogs.forecast_group_dialog(group)

    # ------------------------------------------------------------- trend (clickable years)
    with c2, st.container(key="card_trend"):
        t.card_title("At-risk", "Trend", "Share at risk by audit year · click a point for that year's breakdown")
        scores = core.load_scores()
        actual = (scores.dropna(subset=["actual_next_outcome"]).groupby("audit_year")["actual_next_outcome"]
                  .apply(lambda s: (s == "at_risk").mean()))
        fig = go.Figure()
        fig.add_scatter(x=actual.index, y=actual.values * 100, mode="lines+markers", name="Actual",
                        line=dict(color=t.TEAL, width=3, shape="spline"), fill="tozeroy",
                        fillcolor="rgba(32,195,176,0.25)", marker=dict(size=11, color=t.TEAL),
                        customdata=list(actual.index), hovertemplate="%{x} audit<br>%{y:.1f}% at risk<extra></extra>")
        fc_share = flagged / n * 100
        fig.add_scatter(x=[actual.index.max(), core.FORECAST_AUDIT_YEAR], y=[actual.values[-1] * 100, fc_share],
                        mode="lines+markers", name="Forecast", line=dict(color=t.PINK, width=3, dash="dash"),
                        marker=dict(size=[0, 14], color=t.PINK, symbol="star"),
                        customdata=[actual.index.max(), core.FORECAST_AUDIT_YEAR],
                        hovertemplate="%{x} audit (forecast)<br>%{y:.1f}% predicted at risk<extra></extra>")
        fig.update_yaxes(title="% of municipalities at risk", range=[0, 70], ticksuffix="%")
        fig.update_xaxes(title="Audit year", dtick=1)
        event = st.plotly_chart(t.style_fig(fig, 320), width="stretch", on_select="rerun", selection_mode="points",
                                key=nav.chart_key("trend"), config={"displayModeBar": False})
        year = nav.clicked(event)
        if year is not None:
            nav._bump()  # clear the selection so the dialog does not reopen
            dialogs.year_dialog(int(year))

    st.write("")
    c3, c4 = st.columns([1.15, 1])
    # ------------------------------------------------------------- top 10 forecast (clickable)
    with c3, st.container(key="card_top"):
        t.card_title("Highest", "Risk", f"Top 10 forecast for the {core.FORECAST_AUDIT_YEAR} audit · click a bar "
                     "to open the municipality")
        top = fc.sort_values("risk_probability", ascending=False).head(10).iloc[::-1]
        fig = go.Figure(go.Bar(
            x=top["risk_probability"] * 100, y=top["Name"], orientation="h", customdata=top["demarcation.code"],
            marker=dict(color=top["risk_probability"], colorscale=[[0, t.ORANGE], [1, t.PINK]]),
            text=[f"{p:.0%}" for p in top["risk_probability"]], textposition="outside",
            hovertemplate="%{y}: %{x:.1f}%<extra>click to open</extra>"))
        fig.update_xaxes(range=[0, 110], title="Forecast risk (%)", ticksuffix="%")
        event = st.plotly_chart(t.style_fig(fig, 360, legend=False), width="stretch", on_select="rerun",
                                selection_mode="points", key=nav.chart_key("top10"), config={"displayModeBar": False})
        code = nav.clicked(event)
        if code:
            nav.open_profile(code)

    # ------------------------------------------------------------- province snapshot (clickable)
    with c4, st.container(key="card_prov"):
        t.card_title("Province", "Snapshot", f"Share forecast at risk in {core.FORECAST_AUDIT_YEAR} · click a province "
                     "to explore it")
        prov = fc.groupby("province").agg(share=("predicted_outcome", lambda s: (s == "at_risk").mean()),
                                         n=("demarcation.code", "size")).sort_values("share")
        fig = go.Figure(go.Bar(
            x=prov["share"] * 100, y=prov.index, orientation="h", customdata=list(prov.index),
            marker=dict(color=prov["share"], colorscale=[[0, t.GREEN], [0.5, t.ORANGE], [1, t.PINK]], cmin=0, cmax=1),
            text=[f"{s:.0%} of {k}" for s, k in zip(prov["share"], prov["n"])], textposition="outside",
            hovertemplate="%{y}: %{x:.0f}% at risk<extra>click to explore</extra>"))
        fig.update_xaxes(range=[0, 125], ticksuffix="%", title="Forecast at risk")
        event = st.plotly_chart(t.style_fig(fig, 360, legend=False), width="stretch", on_select="rerun",
                                selection_mode="points", key=nav.chart_key("prov"), config={"displayModeBar": False})
        province = nav.clicked(event)
        if province:
            nav.open_explore(province=[province])

    st.write("")
    # ------------------------------------------------------------- leaderboard (clickable)
    with st.container(key="card_leader"):
        t.card_title("Model", "Leaderboard", "Validation year 2022 — macro-F1 (bars) and ROC-AUC (diamonds) · "
                     "click a bar for that model's details")
        val = core.load_csv("q4_validation_metrics.csv")
        fig = go.Figure()
        fig.add_bar(x=val["model"], y=val["val_macro_f1"], name="Macro-F1", customdata=val["model"],
                    marker_color=[t.MODEL_COLORS[x] for x in val["model"]],
                    text=[f"{v:.2f}" for v in val["val_macro_f1"]], textposition="inside",
                    insidetextanchor="middle", textfont=dict(color="white"))
        fig.add_scatter(x=val["model"], y=val["val_roc_auc"], name="ROC-AUC", mode="markers",
                        marker=dict(symbol="diamond", size=12, color=t.PINK), hoverinfo="skip")
        fig.update_yaxes(range=[0, 1.1])
        event = st.plotly_chart(t.style_fig(fig, 320), width="stretch", on_select="rerun", selection_mode="points",
                                key=nav.chart_key("leader"), config={"displayModeBar": False})
        model = nav.clicked(event)
        if model:
            nav._bump()
            dialogs.model_dialog(model)

    st.write("")
    st.html('<div class="notice"><b>Responsible use:</b> this tool supports — and does not replace — the '
            'Auditor-General\'s audit or Treasury\'s judgement. Use it to prioritise support, never to punish '
            'a municipality or to decide funding on its own. See <i>About & responsible use</i>.</div>')
