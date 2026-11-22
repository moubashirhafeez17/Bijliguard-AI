"""Theft detection page: search a meter, see its history, flagged list, try a reading."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.components import alerts, charts, metric_cards, sidebar  # noqa: E402
from app.utils import formatting as fmt, helpers  # noqa: E402
from src.services import prediction_service as svc  # noqa: E402

data = helpers.load_all()
f = sidebar.render_sidebar(data)
theft, _ = helpers.apply_filters(data["theft"], data["trf"], f)
latest = helpers.latest_theft(theft, f["as_of_month"])

st.title("Electricity Theft Detection")
metric_cards.disclaimer()

n = len(latest)
n_susp = int((latest["label"] == "Suspicious").sum())
metric_cards.metric_row([
    ("Meters in selection", f"{n:,}", None),
    ("Suspicious", f"{n_susp:,}", "Risk score of 50% or more"),
    ("Share suspicious", fmt.pct(n_susp / n if n else 0, 1), None),
    ("Average risk score", fmt.pct(latest["risk_score"].mean() if n else 0, 1), None),
])

tab_search, tab_list, tab_try = st.tabs(["Meter search", "Flagged meters", "Try a reading"])

# ------------------------------------------------------------ meter search
with tab_search:
    only_susp = st.toggle("Only list suspicious meters", value=False)
    pool = latest[latest["label"] == "Suspicious"] if only_susp else latest
    ids = pool.sort_values("risk_score", ascending=False)["meter_id"].tolist()
    if not ids:
        st.info("No meters match the current filters.")
    else:
        typed = st.text_input("Search by meter ID", placeholder="e.g. MTR-00042")
        if typed:
            ids = [i for i in ids if typed.strip().upper() in i] or ids
        meter_id = st.selectbox("Meter", ids, help="Sorted by highest risk first.")
        m = theft[theft["meter_id"] == meter_id].sort_values("month")
        cur = m[m["month"] == f["as_of_month"]].iloc[-1] if (m["month"] == f["as_of_month"]).any() else m.iloc[-1]

        c1, c2 = st.columns([1, 2])
        with c1:
            with st.container(border=True):
                st.markdown(f"**{meter_id}**  \n{cur['area']} · {cur['meter_type']}")
                st.markdown(fmt.badge(cur["label"], cur["label"]), unsafe_allow_html=True)
                st.metric("Risk score", fmt.pct(cur["risk_score"], 0))
                st.metric("This month", fmt.units(cur["monthly_units"]),
                          delta=f"{cur['change_pct']:+.0f}% vs last month", delta_color="off")
                st.write(cur["recommendation"])
        with c2:
            st.plotly_chart(charts.meter_timeline(m), width="stretch")

        with st.expander("Reading history"):
            st.dataframe(
                m[["month", "monthly_units", "previous_units", "bill_amount_pkr", "temperature_c",
                   "label", "risk_score"]].rename(columns={
                    "month": "Month", "monthly_units": "Units", "previous_units": "Previous units",
                    "bill_amount_pkr": "Bill (PKR)", "temperature_c": "Temp (°C)",
                    "label": "Result", "risk_score": "Risk"}),
                hide_index=True, width="stretch",
                column_config={"Month": st.column_config.DateColumn(format="MMM YYYY"),
                               "Risk": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent")})

# ------------------------------------------------------------ flagged list
with tab_list:
    left, right = st.columns([3, 2])
    with left:
        flagged = latest[latest["label"] == "Suspicious"].sort_values("risk_score", ascending=False)
        st.subheader(f"{len(flagged)} flagged meters · {f['as_of_month']:%b %Y}")
        st.dataframe(
            flagged[["meter_id", "area", "meter_type", "monthly_units", "change_pct", "risk_score"]].rename(columns={
                "meter_id": "Meter", "area": "Area", "meter_type": "Type", "monthly_units": "Units",
                "change_pct": "Change vs last month (%)", "risk_score": "Risk"}),
            hide_index=True, width="stretch", height=420,
            column_config={"Risk": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent")})
        st.download_button("Download flagged list (CSV)", flagged.to_csv(index=False).encode(),
                           file_name="flagged_meters.csv", mime="text/csv")
    with right:
        st.subheader("Top alerts")
        alerts.theft_alerts(latest, limit=4)
    st.plotly_chart(charts.theft_risk_hist(latest), width="stretch")

# ------------------------------------------------------------ try a reading
with tab_try:
    st.write("Enter a reading to see how the model would treat it.")
    c1, c2, c3, c4 = st.columns(4)
    usual = c1.number_input("Usual monthly units", 50, 5000, 350, step=10)
    prev = c2.number_input("Last month's units", 0, 5000, 340, step=10)
    now = c3.number_input("This month's units", 0, 5000, 90, step=10)
    temp = c4.slider("Temperature (°C)", 10, 45, 30)
    res = svc.predict_single_meter(now, prev, temp, usual_units=usual)
    with st.container(border=True):
        st.markdown(fmt.badge(res["label"], res["label"]), unsafe_allow_html=True)
        st.metric("Risk score", fmt.pct(res["risk_score"], 0))
        st.write(res["recommendation"])
        st.caption("A lower reading does not prove theft; there may be a valid reason.")
