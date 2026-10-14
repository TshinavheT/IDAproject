"""
Municipality profile: how one municipality has performed (audit opinions, financial
health, model risk over time) and its forecast for the next audit.
Opened from any chart, table or dialog via ?code=<demarcation code>.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import core
import nav
import theme as t

OUTCOME_LABEL = {"at_risk": "At risk", "not_at_risk": "Not at risk"}
SPLIT_SYMBOL = {"fitted": "circle", "test": "diamond", "forecast": "star"}

# MFMA Circular 71 norms where one exists for our definition of the ratio.
NORMS = {
    "cash_coverage_ratio": (">=", 1.0, "≥ 1 month"),
    "collection_rate": (">=", 0.95, "≥ 95%"),
    "debtor_days": ("<=", 30.0, "≤ 30 days"),
    "irregular_expenditure_ratio": ("<=", 0.0, "0%"),
    "operating_surplus": (">=", 0.0, "surplus ≥ 0"),
}
TREND_FEATURES = ["cash_coverage_ratio", "collection_rate", "debtor_days",
                  "repairs_maintenance_ratio", "irregular_expenditure_ratio", "operating_surplus"]


def _scale(feature, values):
    kind = core.FEATURE_INFO[feature]["kind"]
    if kind == "pct":
        return values * 100, "%"
    if kind == "rand":
        return values / 1e6, "R m"
    return values, {"months": "months", "days": "days"}.get(kind, "")


def _meets(feature, value):
    if feature not in NORMS or pd.isna(value):
        return None
    op, threshold, _ = NORMS[feature]
    return value >= threshold if op == ">=" else value <= threshold


def profile():
    scores = core.load_scores()
    names = scores.drop_duplicates("demarcation.code").sort_values("Name")
    options = dict(zip(names["demarcation.code"], names["Name"] + " (" + names["demarcation.code"] + ")"))

    code = st.query_params.get("code")
    if code not in options:
        code = None
    picked = st.selectbox("Municipality", list(options), index=list(options).index(code) if code else None,
                          format_func=options.get, placeholder="Search for a municipality…",
                          key=nav.chart_key("profile_pick"))
    if picked and picked != code:
        st.query_params["code"] = picked
        st.rerun()
    if not picked:
        t.header("Municipality", "Profile", "Choose a municipality to see its audit history, financial health and "
                 "forecast for the next audit", len(options), "municipalities")
        return
    code = picked

    hist = core.municipality(code)
    latest = hist.iloc[-1]
    forecast = hist[hist["split"] == "forecast"]
    current = forecast.iloc[-1] if len(forecast) else latest
    history = core.audit_history(code)
    streak_outcome, streak_years = core.opinion_streak(history)

    t.header(latest["Name"], "", f"{code} · {latest['category']} municipality · {latest['province']}",
             f"{current['risk_probability']:.0%}", f"{int(current['audit_year'])}<br>risk")

    # ------------------------------------------------------------- forecast card
    fc_all = core.forecast_rows()
    with st.container(key="card_pf_forecast"):
        is_forecast = current["split"] == "forecast"
        t.card_title("Next audit", "Forecast" if is_forecast else "Prediction",
                     f"{int(current['audit_year'])} audit, from audited {int(current['financial_year_end.year'])} figures"
                     + ("" if is_forecast else " (no newer figures published)"))
        a, b, c = st.columns([1.1, 1.5, 1])
        label = current["predicted_outcome"]
        with a:
            st.plotly_chart(t.semi_gauge(current["risk_probability"] * 100, "Probability of a poor audit",
                                         t.RISK_COLORS[label]), width="stretch", config={"displayModeBar": False})
            st.html(f'<div style="text-align:center">{t.pill(OUTCOME_LABEL[label], t.RISK_COLORS[label])}'
                    f'<div class="card-sub" style="margin-top:8px">{core.confidence_words(current["risk_probability"])}</div></div>')
        with b:
            row = hist.iloc[[len(hist) - 1]] if not len(forecast) else forecast.iloc[[-1]]
            drivers = core.explain(row)
            items = "".join(f"<li>{line}</li>" for line in core.plain_language(current["risk_probability"], label, drivers))
            st.html(f'<ul class="explain">{items}</ul>')
        with c:
            if is_forecast:
                rank = int((fc_all["risk_probability"] > current["risk_probability"]).sum()) + 1
                prov = fc_all[fc_all["province"] == current["province"]]
                prov_rank = int((prov["risk_probability"] > current["risk_probability"]).sum()) + 1
                t.stat(f"#{rank} of {len(fc_all)}", "nationally (1 = highest risk)", t.PINK, "#")
                t.stat(f"#{prov_rank} of {len(prov)}", f"in {current['province']}", t.ORANGE, "⌂")
            if streak_outcome:
                t.stat(f"{streak_years} yr", f"{OUTCOME_LABEL[streak_outcome].lower()} streak", t.TEAL, "↻")

    st.write("")
    # ------------------------------------------------------------- risk history
    left, right = st.columns([1.45, 1])
    with left, st.container(key="card_pf_history"):
        t.card_title("Risk", "History", "Model risk for each audit year · marker colour = what actually happened")
        fig = go.Figure()
        fitted = hist[hist["split"] == "fitted"]
        if len(fitted):
            fig.add_vrect(x0=fitted["audit_year"].min() - 0.5, x1=fitted["audit_year"].max() + 0.5,
                          fillcolor="#DDE3EC", opacity=0.35, line_width=0, layer="below",
                          annotation_text="model trained on these years", annotation_position="top left",
                          annotation_font=dict(size=10, color=t.MUTED))
        fig.add_hline(y=50, line=dict(color=t.MUTED, dash="dot", width=1),
                      annotation_text="50% threshold", annotation_position="bottom right",
                      annotation_font=dict(size=10, color=t.MUTED))
        fig.add_scatter(x=hist["audit_year"], y=hist["risk_probability"] * 100, mode="lines",
                        line=dict(color=t.BLUE, width=3, shape="spline"), showlegend=False, hoverinfo="skip")
        actual_color = hist["actual_next_outcome"].map(t.RISK_COLORS).fillna(t.MUTED)
        hover = [f"{int(r.audit_year)} audit · {core.SPLIT_LABEL[r.split]}<br>Model risk {r.risk_probability:.0%}<br>"
                 f"Actual: {str(r.actual_next_opinion_raw).replace('_', ' ') if isinstance(r.actual_next_opinion_raw, str) else 'not yet published'}"
                 for r in hist.itertuples()]
        fig.add_scatter(x=hist["audit_year"], y=hist["risk_probability"] * 100, mode="markers",
                        marker=dict(size=16, color=actual_color, symbol=[SPLIT_SYMBOL[s] for s in hist["split"]],
                                    line=dict(color="white", width=2)),
                        hovertext=hover, hoverinfo="text", showlegend=False)
        for name, color, symbol in (("Actual: poor audit", t.PINK, "circle"), ("Actual: clean audit", t.GREEN, "circle"),
                                    ("Held-out test year", t.MUTED, "diamond"), ("Forecast (not yet known)", t.MUTED, "star")):
            fig.add_scatter(x=[None], y=[None], mode="markers", name=name,
                            marker=dict(size=11, color=color, symbol=symbol))
        fig.update_yaxes(range=[0, 105], title="Model risk (%)", ticksuffix="%")
        fig.update_xaxes(title="Audit year", dtick=1)
        st.plotly_chart(t.style_fig(fig, 340), width="stretch", config={"displayModeBar": False})

    with right, st.container(key="card_pf_opinions"):
        t.card_title("Audit", "Opinions", "Auditor-General outcome by financial year")
        years = list(history)
        ops = [history[y] for y in years]
        fig = go.Figure(go.Bar(
            x=years, y=[1] * len(years), marker_color=[core.OPINION_COLORS.get(o, t.MUTED) for o in ops],
            text=[str(o).replace("_", " ").replace("unqualified emphasis of matter", "unqualified + findings")
                  for o in ops], textposition="inside", textangle=-90, insidetextanchor="middle",
            textfont=dict(color="white", size=11), hovertemplate="%{x}: %{text}<extra></extra>"))
        fig.update_yaxes(visible=False, range=[0, 1])
        fig.update_xaxes(dtick=1)
        st.plotly_chart(t.style_fig(fig, 250, legend=False), width="stretch", config={"displayModeBar": False})
        chips = "".join(f'<span class="chip" style="background:{c}">{k.replace("_", " ")}</span>'
                        for k, c in core.OPINION_COLORS.items())
        st.html(f'<div class="card-sub">{chips}</div>')

    st.write("")
    # ------------------------------------------------------------- financial trends
    with st.container(key="card_pf_trends"):
        t.card_title("Financial", "Health", "Audited indicators by financial year · dashed line = national median")
        national = scores.groupby("financial_year_end.year")[TREND_FEATURES].median()
        fig = make_subplots(rows=2, cols=3, subplot_titles=[core.FEATURE_INFO[f]["label"] for f in TREND_FEATURES],
                            vertical_spacing=0.18, horizontal_spacing=0.07)
        for i, f in enumerate(TREND_FEATURES):
            r, c = i // 3 + 1, i % 3 + 1
            own, unit = _scale(f, hist[f])
            med, _ = _scale(f, national[f])
            fig.add_scatter(x=hist["financial_year_end.year"], y=own, mode="lines+markers", row=r, col=c,
                            line=dict(color=t.PINK, width=2.5), marker=dict(size=7), showlegend=False,
                            hovertemplate=f"%{{x}}: %{{y:,.1f}} {unit}<extra>{latest['Name']}</extra>")
            fig.add_scatter(x=national.index, y=med, mode="lines", row=r, col=c,
                            line=dict(color=t.MUTED, width=1.5, dash="dash"), showlegend=False,
                            hovertemplate=f"%{{x}}: %{{y:,.1f}} {unit}<extra>National median</extra>")
            fig.update_yaxes(title_text=unit, row=r, col=c, title_font=dict(size=10))
            fig.update_xaxes(dtick=2, row=r, col=c)
        fig.update_annotations(font_size=12)
        st.plotly_chart(t.style_fig(fig, 490, legend=False).update_layout(margin=dict(t=34)), width="stretch",
                        config={"displayModeBar": False})

    st.write("")
    # ------------------------------------------------------------- peer comparison
    with st.container(key="card_pf_peers"):
        year = int(current["financial_year_end.year"])
        t.card_title("Peer", "Comparison", f"Financial year {year} · against {current['province']} and all municipalities")
        same_year = scores[scores["financial_year_end.year"] == year]
        prov_med = same_year[same_year["province"] == current["province"]][core.NUMERIC_FEATURES].median()
        cat_med = same_year[same_year["category"] == current["category"]][core.NUMERIC_FEATURES].median()
        nat_med = same_year[core.NUMERIC_FEATURES].median()
        rows = []
        for f in core.NUMERIC_FEATURES:
            if f == "total_expenditure":
                continue
            meets = _meets(f, current[f])
            rows.append({
                "Indicator": core.FEATURE_INFO[f]["label"],
                "This municipality": core.fmt_value(f, current[f]),
                f"{current['province']} median": core.fmt_value(f, prov_med[f]),
                f"{current['category']} median": core.fmt_value(f, cat_med[f]),
                "National median": core.fmt_value(f, nat_med[f]),
                "Treasury norm": NORMS.get(f, (None, None, "—"))[2],
                "Status": "—" if meets is None else ("✅ meets norm" if meets else "⚠️ below norm"),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption("Norms from National Treasury MFMA Circular 71. Repairs & maintenance and grant dependency have no "
                   "directly comparable norm for these definitions. Raw Municipal Money figures can contain reporting "
                   "errors — extreme values should be checked against the audited financial statements.")

    st.write("")
    c1, c2 = st.columns(2)
    if c1.button("← Back to the Explorer", width="stretch"):
        nav.open_explore(province=[current["province"]])
    if c2.button("Score this municipality with my own figures", width="stretch"):
        nav.open_page("risk")
