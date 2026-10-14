"""
Navigation helpers for drill-downs: open a municipality profile or the explorer
from any chart, table or dialog.

Charts and tables that navigate use chart_key(), which changes after every
navigation, so a selection made before leaving a page does not fire again when
the user comes back.
"""

import streamlit as st

PAGES = {}  # filled by app.py on every run: {"profile": st.Page, "explore": st.Page, ...}


def chart_key(name):
    return f"{name}_{st.session_state.get('nav_nonce', 0)}"


def _bump():
    st.session_state["nav_nonce"] = st.session_state.get("nav_nonce", 0) + 1


def _go(page, query_params=None):
    # st.switch_page does not leave the page when called inside a dialog (a fragment), so record
    # the destination and rerun the whole app; app.py switches page before rendering anything.
    st.session_state["nav_goto"] = (page, query_params or {})
    _bump()
    st.rerun(scope="app")


def follow_pending():
    """Called by app.py after st.navigation() and before page.run()."""
    goto = st.session_state.pop("nav_goto", None)
    if goto:
        page, params = goto
        st.switch_page(PAGES[page], query_params=params or None)


def open_profile(code):
    _go("profile", {"code": code})


def open_page(page):
    _go(page)


def open_explore(**filters):
    """Open the explorer with filters pre-set (province, category, opinion, year, band)."""
    st.session_state["explore_pending"] = filters
    _go("explore")


def clicked(event, field="customdata"):
    """First selected point's value from a plotly on_select event, or None."""
    try:
        points = event.selection.points
    except AttributeError:
        return None
    if not points:
        return None
    point = points[0]
    value = point.get(field)
    if isinstance(value, (list, tuple)):
        value = value[0]
    return value


def selected_row(event):
    """Index of the first selected row from a dataframe on_select event, or None."""
    try:
        rows = event.selection.rows
    except AttributeError:
        return None
    return rows[0] if rows else None
