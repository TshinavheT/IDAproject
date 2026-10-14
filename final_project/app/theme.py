"""
Visual theme for the dashboard: soft neumorphic cards, gradient ring gauges and
Plotly styling, following the KPI-dashboard reference design.
"""

import base64
import itertools

import plotly.graph_objects as go
import streamlit as st

BG = "#E9EDF3"
CARD = "#F1F4F8"
INK = "#2E3546"
MUTED = "#7A8396"
TRACK = "#DDE3EC"

PINK, ORANGE, GREEN, TEAL, BLUE, PURPLE = "#F0507A", "#F5A524", "#22B07D", "#20C3B0", "#3B8DEB", "#8B5CF6"
GRADIENTS = {
    "pink": ("#FF7A9C", "#E83E6C"),
    "orange": ("#FFC25C", "#F08A1C"),
    "green": ("#45D19B", "#139A68"),
    "blue": ("#6CB6FF", "#3B6FEB"),
    "purple": ("#B48CFF", "#7A4CF0"),
    "teal": ("#5BE0CF", "#14A396"),
}
MODEL_COLORS = {
    "Baseline (Dummy)": "#A0A8B8",
    "Baseline (Repeat last year)": "#5B6475",
    "Logistic Regression": BLUE,
    "Random Forest": GREEN,
    "MLP": ORANGE,
    "Residual Tabular NN": PURPLE,
}
RISK_COLORS = {"at_risk": PINK, "not_at_risk": GREEN}

_ids = itertools.count()

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"], .stApp, .stMarkdown, button, input, select, textarea {{
  font-family: 'Poppins', sans-serif !important;
}}
.stApp {{ background: {BG}; color: {INK}; }}
header[data-testid="stHeader"] {{ background: {BG}; }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 3rem; max-width: 1320px; }}
h1, h2, h3, h4 {{ color: {INK}; font-family: 'Poppins', sans-serif !important; }}

[class*="st-key-card"] {{
  background: {CARD};
  border-radius: 22px;
  padding: 18px 20px 14px 20px;
  box-shadow: 9px 9px 20px #CBD2DD, -9px -9px 20px #FFFFFF;
}}
[class*="st-key-card"] [data-testid="stPlotlyChart"] {{ margin-top: -6px; }}

.hdr {{ display:flex; align-items:center; justify-content:space-between; margin-bottom: 6px; }}
.hdr .dots span {{ display:inline-block; width:12px; height:12px; border-radius:4px; margin-right:6px; }}
.hdr h1 {{ font-size: 2.3rem; font-weight: 400; margin: 6px 0 0 0; padding:0; line-height:1.15; }}
.hdr h1 b {{ font-weight: 700; }}
.hdr p {{ color: {MUTED}; margin: 4px 0 0 0; font-size: .92rem; }}
.badge {{ width:86px; height:86px; border-radius:50%; background:{CARD}; display:flex; flex-direction:column;
  align-items:center; justify-content:center; box-shadow: 8px 8px 18px #CBD2DD, -8px -8px 18px #FFFFFF; }}
.badge b {{ font-size:1.45rem; color:{INK}; line-height:1; }}
.badge small {{ font-size:.62rem; color:{MUTED}; margin-top:3px; text-align:center; }}

.card-title {{ font-size: 1.05rem; font-weight: 400; color:{INK}; margin: 0 0 2px 0; }}
.card-title b {{ font-weight: 700; }}
.mini-dots span {{ display:inline-block; width:5px; height:5px; border-radius:50%; margin-right:3px; }}
.card-sub {{ color:{MUTED}; font-size:.78rem; margin: 2px 0 8px 0; }}

.ring-wrap {{ display:flex; flex-direction:column; align-items:center; text-align:center; }}
.ring {{ width: 112px; height:112px; border-radius:50%; background:{CARD}; display:flex; align-items:center;
  justify-content:center; box-shadow: inset 5px 5px 10px #D3D9E3, inset -5px -5px 10px #FFFFFF; }}
.ring-label {{ font-size:.8rem; font-weight:600; color:{INK}; margin-top:10px; }}
.ring-note {{ font-size:.7rem; color:{MUTED}; margin-top:2px; max-width:150px; }}

.stat {{ display:flex; align-items:center; gap:12px; padding:4px 0; }}
.stat .icon {{ width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center;
  color:white; font-size:1rem; box-shadow: 3px 3px 8px #CBD2DD; }}
.stat .val {{ font-size:1.35rem; font-weight:700; line-height:1.1; }}
.stat .lbl {{ font-size:.74rem; color:{MUTED}; }}

.pill {{ display:inline-block; padding:5px 14px; border-radius:999px; font-weight:600; font-size:.85rem; color:white; }}
.explain li {{ margin-bottom: 6px; font-size:.9rem; }}
.up {{ color:{PINK}; font-weight:600; }}
.down {{ color:{GREEN}; font-weight:600; }}
.notice {{ background:#FFF6E5; border-left:4px solid {ORANGE}; border-radius:12px; padding:10px 14px;
  font-size:.82rem; color:#6B5320; }}
.chip {{ display:inline-block; padding:3px 10px; border-radius:999px; font-size:.72rem; font-weight:600;
  color:white; margin:2px 4px 2px 0; }}
.mtable {{ width:100%; border-collapse:separate; border-spacing:10px; }}
.mtable td {{ background:{CARD}; border-radius:16px; text-align:center; padding:14px 6px;
  box-shadow: inset 4px 4px 9px #D3D9E3, inset -4px -4px 9px #FFFFFF; }}
.mtable td b {{ display:block; font-size:1.7rem; }}
.mtable td small {{ color:{MUTED}; font-size:.72rem; }}

[data-testid="stMetricValue"] {{ font-size: 1.25rem; font-weight: 600; }}
[data-testid="stMetricLabel"] p {{ font-size: .76rem; color: {MUTED}; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
.stTabs [data-baseweb="tab"] {{ background:{CARD}; border-radius:14px; padding:8px 18px;
  box-shadow: 4px 4px 10px #CBD2DD, -4px -4px 10px #FFFFFF; }}
.stTabs [aria-selected="true"] {{ color:{PINK} !important; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display:none; }}
div.stButton > button, div.stFormSubmitButton > button, div.stDownloadButton > button {{
  border-radius: 14px; border: none; background: linear-gradient(135deg, #FF7A9C, #E83E6C);
  color: white; font-weight: 600; box-shadow: 4px 4px 12px #CBD2DD;
}}
div.stButton > button[data-testid="stBaseButton-tertiary"] {{
  background: none; box-shadow: none; color: {PINK}; font-size: .8rem; font-weight: 600;
  min-height: 0; padding: 2px 6px; margin-top: 2px;
}}
div.stButton > button[data-testid="stBaseButton-tertiary"]:hover {{ color: #C8335B; text-decoration: underline; }}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def header(title_light, title_bold, subtitle, badge_value, badge_label):
    st.html(f"""
<div class="hdr">
  <div>
    <div class="dots"><span style="background:{PINK}"></span><span style="background:{ORANGE}"></span><span style="background:{TEAL}"></span></div>
    <h1>{title_light} <b>{title_bold}</b></h1>
    <p>{subtitle}</p>
  </div>
  <div class="badge"><b>{badge_value}</b><small>{badge_label}</small></div>
</div>""")


def card_title(light, bold="", sub=""):
    dots = f'<div class="mini-dots"><span style="background:{PINK}"></span><span style="background:{ORANGE}"></span><span style="background:{TEAL}"></span></div>'
    sub_html = f'<div class="card-sub">{sub}</div>' if sub else ""
    st.html(f'<div class="card-title">{light} <b>{bold}</b></div>{dots}{sub_html}')


def ring(value, label, note="", color="pink", text=None):
    """Gradient progress ring. value in 0-1."""
    gid = f"g{next(_ids)}"
    start, end = GRADIENTS[color]
    r, circ = 40, 2 * 3.14159 * 40
    dash = max(0.0, min(1.0, value)) * circ
    text = text or f"{value * 100:.0f}%"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 100 100">
<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="{start}"/><stop offset="100%" stop-color="{end}"/></linearGradient></defs>
<circle cx="50" cy="50" r="{r}" fill="none" stroke="{TRACK}" stroke-width="9"/>
<circle cx="50" cy="50" r="{r}" fill="none" stroke="url(#{gid})" stroke-width="9" stroke-linecap="round"
 stroke-dasharray="{dash:.1f} {circ:.1f}" transform="rotate(-90 50 50)"/>
<text x="50" y="56" text-anchor="middle" font-family="Poppins, Segoe UI, sans-serif" font-size="19"
 font-weight="700" fill="{INK}">{text}</text></svg>"""
    # st.html sanitises inline <svg>, so the ring is embedded as an image instead.
    src = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    st.html(f"""
<div class="ring-wrap">
  <div class="ring"><img src="{src}" width="96" height="96" alt="{label}: {text}"/></div>
  <div class="ring-label">{label}</div>
  <div class="ring-note">{note}</div>
</div>""")


def stat(value, label, color=PINK, icon="●"):
    st.html(f"""
<div class="stat"><div class="icon" style="background:{color}">{icon}</div>
<div><div class="val">{value}</div><div class="lbl">{label}</div></div></div>""")


def pill(text, color):
    return f'<span class="pill" style="background:{color}">{text}</span>'


def style_fig(fig, height=300, legend=True):
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=10, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Poppins, sans-serif", color=INK, size=12),
        showlegend=legend, barcornerradius=8,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
        hoverlabel=dict(font_family="Poppins, sans-serif"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=TRACK, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor="#E1E6EE", zeroline=False, tickfont=dict(color=MUTED))
    return fig


def semi_gauge(value, title, color, suffix="%", max_value=100):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number=dict(suffix=suffix, font=dict(size=26, color=INK)),
        title=dict(text=title, font=dict(size=13, color=MUTED)),
        gauge=dict(
            axis=dict(range=[0, max_value], visible=False),
            bar=dict(color=color, thickness=0.32),
            bgcolor=TRACK, borderwidth=0,
            steps=[dict(range=[0, max_value], color=TRACK)],
        ),
    ))
    return style_fig(fig, height=190, legend=False).update_layout(margin=dict(l=18, r=18, t=40, b=0))
