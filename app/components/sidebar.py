"""Shared sidebar: filters that apply to every page."""
import streamlit as st

from config import settings as S


def render_sidebar(data):
    theft, trf = data["theft"], data["trf"]
    st.sidebar.markdown("### BijliGuard")
    st.sidebar.caption("AI electricity monitoring prototype")

    areas = st.sidebar.multiselect("Areas", S.AREA_NAMES, default=S.AREA_NAMES, key="f_areas")
    meter_types = st.sidebar.multiselect("Meter types", S.METER_TYPES, default=S.METER_TYPES, key="f_types")

    months = sorted(theft["month"].unique())
    as_of_month = st.sidebar.select_slider(
        "Billing month", options=months, value=months[-1],
        format_func=lambda d: f"{d:%b %Y}", key="f_month")

    dates = sorted(trf["date"].unique())
    as_of_date = st.sidebar.select_slider(
        "Transformer date", options=dates, value=dates[-1],
        format_func=lambda d: f"{d:%d %b %Y}", key="f_date")

    st.sidebar.divider()
    src = theft["source"].iloc[0] if "source" in theft else "unknown"
    st.sidebar.caption(
        "**Data:** synthetic Karachi-style records (simulated).  \n"
        f"**Predictions:** {src}.")
    if not areas:
        st.sidebar.warning("Select at least one area.")
    return {"areas": areas or S.AREA_NAMES, "meter_types": meter_types or S.METER_TYPES,
            "as_of_month": as_of_month, "as_of_date": as_of_date}
