"""Transformer monitoring page: readings, 7-day risk, what-if form."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.components import alerts, charts, metric_cards, sidebar  # noqa: E402
from app.utils import formatting as fmt, helpers  # noqa: E402
from src.services import prediction_service as svc  # noqa: E402

data = helpers.load_all()
f = sidebar.render_sidebar(data)
_, trf = helpers.apply_filters(data["theft"], data["trf"], f)
latest = helpers.latest_trf(trf, f["as_of_date"])

st.title("Transformer Monitoring")
metric_cards.disclaimer()

metric_row_items = [
    ("Transformers", f"{len(latest):,}", f"As of {f['as_of_date']:%d %b %Y}"),
    ("High risk", f"{int((latest['risk_level'] == 'High').sum())}", "7-day failure probability of 30% or more"),
    ("Medium risk", f"{int((latest['risk_level'] == 'Medium').sum())}", "Probability 15-30%"),
    ("Average load", f"{latest['load_pct'].mean():.0f}%" if len(latest) else "n/a", None),
    ("High risk · 30 days", f"{int((helpers.peak_in_window(trf, f['as_of_date'])['risk_level'] == 'High').sum())}",
     "Transformers whose peak estimated risk in the last 30 days reached High"),
]
metric_cards.metric_row(metric_row_items)

tab_one, tab_all, tab_try = st.tabs(["Single transformer", "All transformers", "What-if"])

with tab_one:
    if latest.empty:
        st.info("No transformers match the current filters.")
    else:
        order = latest.sort_values("failure_prob_7d", ascending=False)["transformer_id"].tolist()
        tid = st.selectbox("Transformer", order, help="Sorted by highest risk first.")
        t = trf[trf["transformer_id"] == tid].sort_values("date")
        t = t[t["date"] <= f["as_of_date"]]
        cur = t.iloc[-1]

        c1, c2 = st.columns([1, 2])
        with c1:
            with st.container(border=True):
                st.markdown(f"**{tid}**  \n{cur['area']} · {cur['capacity_kva']} kVA · {cur['age_years']} yrs")
                st.markdown(fmt.badge(f"{cur['risk_level']} risk", cur["risk_level"]), unsafe_allow_html=True)
                st.plotly_chart(charts.risk_gauge(cur["failure_prob_7d"], cur["risk_level"]), width="stretch")
                st.write(cur["recommendation"])
        with c2:
            window = t.tail(90)
            st.plotly_chart(charts.transformer_series(window), width="stretch")

        st.plotly_chart(charts.risk_trend(t.tail(90)), width="stretch")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Load", f"{cur['load_pct']:.0f}%")
        r2.metric("Oil temperature", f"{cur['oil_temp_c']:.0f} °C")
        r3.metric("Ambient", f"{cur['ambient_temp_c']:.0f} °C")
        r4.metric("Humidity", f"{cur['humidity_pct']:.0f}%")

with tab_all:
    left, right = st.columns([3, 2])
    with left:
        shown = latest.sort_values("failure_prob_7d", ascending=False)
        level = st.multiselect("Risk level", ["High", "Medium", "Low"], default=["High", "Medium"])
        shown = shown[shown["risk_level"].isin(level)]
        st.dataframe(
            shown[["transformer_id", "area", "risk_level", "failure_prob_7d", "load_pct", "oil_temp_c", "age_years"]]
            .rename(columns={"transformer_id": "Transformer", "area": "Area", "risk_level": "Risk",
                             "failure_prob_7d": "7-day probability", "load_pct": "Load (%)",
                             "oil_temp_c": "Oil (°C)", "age_years": "Age (yrs)"}),
            hide_index=True, width="stretch", height=420,
            column_config={"7-day probability": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent")})
    with right:
        st.plotly_chart(charts.risk_donut(latest), width="stretch")
        st.subheader("Alerts (last 30 days)")
        win = trf[(trf["date"] <= f["as_of_date"]) & (trf["date"] > f["as_of_date"] - pd.Timedelta(days=30))]
        alerts.transformer_alerts(win.sort_values("failure_prob_7d", ascending=False).drop_duplicates("transformer_id"), limit=4)

with tab_try:
    st.write("Change the readings to see how estimated risk responds.")
    c1, c2, c3, c4 = st.columns(4)
    load = c1.slider("Load (%)", 20, 150, 95)
    oil = c2.slider("Oil temperature (°C)", 40, 120, 88)
    age = c3.slider("Age (years)", 1, 40, 18)
    days = c4.slider("Consecutive overload days", 0, 7, 3)
    res = svc.predict_single_transformer(load, oil, age, days)
    with st.container(border=True):
        st.markdown(fmt.badge(f"{res['risk_level']} risk", res["risk_level"]), unsafe_allow_html=True)
        st.plotly_chart(charts.risk_gauge(res["failure_prob_7d"], res["risk_level"]), width="stretch")
        st.write(res["recommendation"])
