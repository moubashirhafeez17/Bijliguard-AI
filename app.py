"""BijliGuard dashboard entry point.   Run:  streamlit run app.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

st.set_page_config(page_title="BijliGuard", page_icon=":material/bolt:", layout="wide")

from app.components import alerts, charts, metric_cards, sidebar  # noqa: E402
from app.utils import helpers  # noqa: E402


def overview():
    data = helpers.load_all()
    f = sidebar.render_sidebar(data)
    theft, trf = helpers.apply_filters(data["theft"], data["trf"], f)

    t_latest = helpers.latest_theft(theft, f["as_of_month"])
    x_latest = helpers.latest_trf(trf, f["as_of_date"])
    window = trf[(trf["date"] <= f["as_of_date"]) & (trf["date"] > f["as_of_date"] - pd.Timedelta(days=30))]
    peak = helpers.peak_in_window(trf, f["as_of_date"])

    st.title("BijliGuard")
    st.caption("AI-powered electricity theft detection and transformer fault prediction · Karachi (simulated)")
    metric_cards.disclaimer()

    n_susp = int((t_latest["label"] == "Suspicious").sum())
    n_high = int((peak["risk_level"] == "High").sum())
    n_med = int((peak["risk_level"] == "Medium").sum())
    metric_cards.metric_row([
        ("Meters monitored", f"{t_latest['meter_id'].nunique():,}", f"Billing month {f['as_of_month']:%b %Y}"),
        ("Suspicious meters", f"{n_susp:,}", "Flagged for inspection - not proof of theft"),
        ("Transformers monitored", f"{x_latest['transformer_id'].nunique():,}", f"As of {f['as_of_date']:%d %b %Y}"),
        ("High-risk transformers", f"{n_high:,}", "Peak estimated 7-day failure probability of 30% or more in the last 30 days"),
        ("Medium-risk transformers", f"{n_med:,}", "Peak probability of 15-30% in the last 30 days"),
    ])

    area_df = helpers.area_summary(t_latest, window, data["areas"])
    area_df = area_df[area_df["area"].isin(f["areas"])]

    left, right = st.columns([3, 2])
    with left:
        st.plotly_chart(charts.area_risk_bar(area_df), width="stretch")
        st.caption("Area score = half suspicious-meter share, half average transformer failure probability "
                   "over the last 30 days. See the Karachi Area Map page.")
    with right:
        st.plotly_chart(charts.risk_donut(peak, "Transformers by peak risk (30 days)"), width="stretch")
        st.plotly_chart(charts.flagged_by_month(theft), width="stretch")

    a, b = st.columns(2)
    with a:
        st.subheader("Meter alerts")
        alerts.theft_alerts(t_latest)
    with b:
        st.subheader("Transformer alerts")
        alerts.transformer_alerts(peak)
        st.caption("Shows each transformer's highest-risk reading in the last 30 days.")


pages = [
    st.Page(overview, title="Overview", icon=":material/dashboard:", default=True),
    st.Page("app/pages/1_Theft_Detection.py", title="Theft Detection", icon=":material/electric_meter:"),
    st.Page("app/pages/2_Transformer_Monitoring.py", title="Transformer Monitoring", icon=":material/electrical_services:"),
    st.Page("app/pages/3_Karachi_Area_Map.py", title="Karachi Area Map", icon=":material/map:"),
]
st.navigation(pages).run()
