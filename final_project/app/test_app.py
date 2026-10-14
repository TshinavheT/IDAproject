"""
Smoke test for the dashboard: every page renders and every drill-down dialog opens
without an exception. Run from the project root:  python app/test_app.py
"""

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parent
failures = []

PAGE_SCRIPT = """
import sys
sys.path.insert(0, {app_dir!r})
import streamlit as st
import theme
theme.inject_css()
from {module} import {func}
{func}()
"""


def check(at, label):
    errors = [e.value for e in at.exception]
    print(f"{label:60s} {'OK' if not errors else 'FAILED: ' + errors[0][:300]}")
    if errors:
        failures.append(label)


def page(module, func, **query):
    at = AppTest.from_string(PAGE_SCRIPT.format(app_dir=str(APP_DIR), module=module, func=func),
                             default_timeout=180)
    at.query_params.update(query)
    return at.run()


# Full app (navigation + overview)
at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=180).run()
check(at, "app.py (navigation + overview)")

# Every drill-down button on the overview opens its dialog cleanly
overview = page("views_overview", "overview")
check(overview, "Overview page")
for i, button in enumerate(overview.button):
    if button.label in ("Details ›", "See list ›"):
        at = page("views_overview", "overview")
        at.button[i].click().run()
        check(at, f"Overview dialog #{i} ({button.label}, key={button.key})")

# Dialogs opened from chart clicks, called directly
for call in ("year_dialog(2025)", "year_dialog(2021)", "model_dialog('MLP')",
             "model_dialog('Logistic Regression')"):
    script = f"import sys\nsys.path.insert(0, {str(APP_DIR)!r})\nimport dialogs\ndialogs.{call}\n"
    check(AppTest.from_string(script, default_timeout=180).run(), f"dialogs.{call}")

# Explorer and profiles (a metro, a district, a high-risk local, and no selection)
check(page("views_explore", "explore"), "Explorer")
for code in ("NW381", "CPT", "DC25", "ETH"):
    check(page("views_profile", "profile", code=code), f"Profile {code}")
check(page("views_profile", "profile"), "Profile without a municipality")

sys.exit(1 if failures else 0)
