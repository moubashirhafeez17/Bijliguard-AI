"""Karachi map of simulated area-wise risk."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from streamlit_folium import st_folium  # noqa: E402

from app.components import charts, metric_cards, sidebar  # noqa: E402
from app.utils import helpers  # noqa: E402
from src.visualization.karachi_map import build_map, build_offline_figure  # noqa: E402

data = helpers.load_all()
f = sidebar.render_sidebar(data)
theft, trf = helpers.apply_filters(data["theft"], data["trf"], f)

t_latest = helpers.latest_theft(theft, f["as_of_month"])
window = trf[(trf["date"] <= f["as_of_date"]) & (trf["date"] > f["as_of_date"] - pd.Timedelta(days=30))]
area_df = helpers.area_summary(t_latest, window, data["areas"])
area_df = area_df[area_df["area"].isin(f["areas"])]

st.title("Karachi Area Map")
metric_cards.disclaimer()

online = helpers.internet_available()
offline = st.toggle("Offline map (works without internet)", value=not online,
                    help="The street map needs internet. Offline mode draws the areas as risk bubbles "
                         "and works with no connection - use it at the exhibition.")
if not online and not offline:
    st.warning("No internet detected. The street map will not load; switch on offline map.")

left, right = st.columns([3, 2])
with left:
    if offline:
        st.plotly_chart(build_offline_figure(area_df), width="stretch")
    else:
        st_folium(build_map(area_df), height=560, width="stretch", returned_objects=[])
    st.caption("Circle size and colour show the combined area score "
               "(green = low, amber = medium, red = high). Area locations are approximate centres.")
with right:
    st.plotly_chart(charts.area_risk_bar(area_df), width="stretch")

st.subheader("Area details")
st.dataframe(
    area_df.sort_values("risk_score", ascending=False)[
        ["area", "meters", "suspicious_meters", "high_risk_transformers", "avg_fail_prob", "risk_score"]
    ].rename(columns={"area": "Area", "meters": "Meters", "suspicious_meters": "Suspicious meters",
                      "high_risk_transformers": "High-risk transformers (30 days)",
                      "avg_fail_prob": "Avg 7-day failure prob.", "risk_score": "Area score"}),
    hide_index=True, width="stretch",
    column_config={
        "Avg 7-day failure prob.": st.column_config.NumberColumn(format="percent"),
        "Area score": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent")})
