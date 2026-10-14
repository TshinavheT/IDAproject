"""
Municipality explorer: filter by audit year, province, municipality type, last
audit opinion and risk band; click a category bar to filter, click a table row
or a mover to open that municipality's profile.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core
import nav
import theme as t

OUTCOME_LABEL = {"at_risk": "At risk", "not_at_risk": "Not at risk"}
BANDS = {"All": (0, 1.01), "High (≥ 80%)": (0.8, 1.01), "Elevated (50–80%)": (0.5, 0.8), "Low (< 50%)": (0, 0.5)}
DEFAULTS = {"ex_year": core.FORECAST_AUDIT_YEAR, "ex_prov": [], "ex_cat": [], "ex_op": [], "ex_band": "All",
            "ex_search": ""}
PENDING_KEYS = {"year": "ex_year", "province": "ex_prov", "category": "ex_cat", "opinion": "ex_op", "band": "ex_band"}


def _apply_pending():
    """Apply filters requested by another page or a chart click (must run before the widgets)."""
    pending = st.session_state.pop("explore_pending", None)
    if pending is None:
        for k, v in DEFAULTS.items():
            st.session_state.setdefault(k, v)
        return
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    for name, value in pending.items():
        st.session_state[PENDING_KEYS[name]] = value


def _filter_click(name, value):
    current = {k: st.session_state.get(v) for k, v in PENDING_KEYS.items()}
    if name in ("province", "category", "opinion"):
        current[name] = [value]
    else:
        current[name] = value
    st.session_state["explore_pending"] = current
    nav._bump()
    st.rerun()


def _category_chart(df, column, title, sub, key, label_fn=lambda v: v, color_fn=None):
    with st.container(key=f"card_ex_{key}"):
        t.card_title("By", title, sub)
        target = "predicted_outcome"
        grp = df.groupby(column).agg(n=("demarcation.code", "size"),
                                     share=(target, lambda s: (s == "at_risk").mean()),
                                     risk=("risk_probability", "mean")).sort_values("share")
        if grp.empty:
            st.info("No municipalities match the filters.")
            return
        colors = [color_fn(i) for i in grp.index] if color_fn else grp["share"]
        fig = go.Figure(go.Bar(
            x=grp["share"] * 100, y=[label_fn(i) for i in grp.index], orientation="h", customdata=list(grp.index),
            marker=dict(color=colors, colorscale=None if color_fn else [[0, t.GREEN], [0.5, t.ORANGE], [1, t.PINK]],
                        cmin=0, cmax=1),
            text=[f"{s:.0%} · {n}" for s, n in zip(grp["share"], grp["n"])], textposition="outside",
            hovertemplate="%{y}<br>%{x:.0f}% predicted at risk<extra></extra>"))
        fig.update_xaxes(range=[0, 145], ticksuffix="%", title="Predicted at risk", tickvals=[0, 50, 100])
        event = st.plotly_chart(t.style_fig(fig, 60 + 30 * len(grp), legend=False), width="stretch",
                                on_select="rerun", selection_mode="points", key=nav.chart_key(f"ex_{key}"),
                                config={"displayModeBar": False})
        value = nav.clicked(event)
        if value is not None:
            _filter_click({"province": "province", "category": "category", "prior_audit_opinion_raw": "opinion"}[column], value)


def explore():
    _apply_pending()
    years = sorted(core.load_scores()["audit_year"].unique(), reverse=True)
    t.header("Municipality", "Explorer", "Drill into any year, province, type or audit opinion — click a bar to "
             "filter and a row to open a municipality", len(core.forecast_rows()), "municipalities")

    with st.container(key="card_ex_filters"):
        c = st.columns([1.1, 1.4, 1.1, 1.4, 1.1])
        year = c[0].selectbox("Audit year", years, key="ex_year",
                              format_func=lambda y: f"{y} (forecast)" if y == core.FORECAST_AUDIT_YEAR
                              else f"{y} (test year)" if y == 2024 else str(y))
        all_rows = core.year_rows(year)
        provs = c[1].multiselect("Province", sorted(all_rows["province"].unique()), key="ex_prov",
                                 placeholder="All provinces")
        cats = c[2].multiselect("Type", ["Metro", "District", "Local"], key="ex_cat", placeholder="All types")
        ops = c[3].multiselect("Last audit opinion", list(core.OPINION_COLORS), key="ex_op",
                               format_func=lambda s: s.replace("_", " "), placeholder="All opinions")
        band = c[4].selectbox("Risk band", list(BANDS), key="ex_band")
        search = st.text_input("Search by name or code", key="ex_search", placeholder="e.g. Emfuleni or GT421")
        if st.button("Clear all filters", type="tertiary"):
            st.session_state["explore_pending"] = {}
            st.rerun()

    df = all_rows.copy()
    if provs:
        df = df[df["province"].isin(provs)]
    if cats:
        df = df[df["category"].isin(cats)]
    if ops:
        df = df[df["prior_audit_opinion_raw"].isin(ops)]
    lo, hi = BANDS[band]
    df = df[(df["risk_probability"] >= lo) & (df["risk_probability"] < hi)]
    if search:
        s = search.strip().lower()
        df = df[df["Name"].str.lower().str.contains(s, regex=False) | df["demarcation.code"].str.lower().str.contains(s, regex=False)]

    prev = core.year_rows(year - 1)[["demarcation.code", "risk_probability"]].rename(columns={"risk_probability": "prev"})
    df = df.merge(prev, on="demarcation.code", how="left")
    df["change"] = df["risk_probability"] - df["prev"]

    st.write("")
    k = st.columns(4)
    with k[0], st.container(key="card_ex_k1"):
        t.stat(len(df), "municipalities shown", t.BLUE, "▦")
    with k[1], st.container(key="card_ex_k2"):
        t.stat(int((df["predicted_outcome"] == "at_risk").sum()), "predicted at risk", t.PINK, "⚑")
    with k[2], st.container(key="card_ex_k3"):
        t.stat(f"{df['risk_probability'].mean():.0%}" if len(df) else "–", "average risk", t.ORANGE, "%")
    with k[3], st.container(key="card_ex_k4"):
        if year == core.FORECAST_AUDIT_YEAR or df["actual_next_outcome"].isna().all():
            t.stat("not yet", "actual outcomes published", t.TEAL, "…")
        else:
            acc = (df["predicted_outcome"] == df["actual_next_outcome"]).mean() if len(df) else float("nan")
            t.stat(f"{acc:.0%}" if len(df) else "–", "predictions correct", t.TEAL, "✓")

    st.write("")
    a, b, c = st.columns(3)
    with a:
        _category_chart(df, "province", "Province", "Share predicted at risk · click a bar to filter", "prov")
    with b:
        _category_chart(df, "category", "Type", "Metro, district or local · click a bar to filter", "cat")
    with c:
        _category_chart(df, "prior_audit_opinion_raw", "Last opinion", "Most recent AGSA opinion · click a bar to filter", "op",
                        label_fn=lambda v: str(v).replace("_", " ").replace("unqualified emphasis of matter",
                                                                             "unqualified + findings"),
                        color_fn=lambda v: core.OPINION_COLORS.get(v, t.MUTED))

    st.write("")
    left, right = st.columns([1.6, 1])
    with left, st.container(key="card_ex_table"):
        t.card_title("Municipalities", "", f"{year} audit · sorted by risk · click a row to open the profile")
        view = df.sort_values("risk_probability", ascending=False).reset_index(drop=True)
        table = pd.DataFrame({
            "Municipality": view["Name"], "Code": view["demarcation.code"], "Province": view["province"],
            "Type": view["category"],
            "Last opinion": view["prior_audit_opinion_raw"].str.replace("_", " "),
            "Risk": view["risk_probability"], "Change": view["change"] * 100,
            "Prediction": view["predicted_outcome"].map(OUTCOME_LABEL),
            "Actual": view["actual_next_opinion_raw"].fillna("not yet published").str.replace("_", " "),
        })
        event = st.dataframe(table, hide_index=True, width="stretch", height=430, on_select="rerun",
                             selection_mode="single-row", key=nav.chart_key("ex_table"), column_config={
                                 "Risk": st.column_config.ProgressColumn("Risk", format="percent", min_value=0, max_value=1),
                                 "Change": st.column_config.NumberColumn("Δ vs last year", format="%+.0f pts")})
        row = nav.selected_row(event)
        if row is not None:
            nav.open_profile(table.loc[row, "Code"])

    with right, st.container(key="card_ex_movers"):
        t.card_title("Biggest", "Risk increases", f"Change in model risk, {year - 1} → {year} audit · click to open")
        movers = df.dropna(subset=["change"]).sort_values("change", ascending=False).head(10).iloc[::-1]
        movers = movers[movers["change"] > 0.005]
        if movers.empty:
            st.info("No municipality's risk rose by more than half a point for this selection.")
        else:
            fig = go.Figure(go.Bar(
                x=movers["change"] * 100, y=movers["Name"], orientation="h", customdata=movers["demarcation.code"],
                marker=dict(color=movers["change"], colorscale=[[0, t.ORANGE], [1, t.PINK]]),
                text=[f"+{c * 100:.0f} pts" for c in movers["change"]], textposition="outside",
                hovertemplate="%{y}: %{x:+.1f} points<extra></extra>"))
            fig.update_xaxes(title="Increase in risk (percentage points)",
                             range=[0, movers["change"].max() * 130])
            event = st.plotly_chart(t.style_fig(fig, 430, legend=False), width="stretch", on_select="rerun",
                                    selection_mode="points", key=nav.chart_key("ex_movers"),
                                    config={"displayModeBar": False})
            code = nav.clicked(event)
            if code:
                nav.open_profile(code)
