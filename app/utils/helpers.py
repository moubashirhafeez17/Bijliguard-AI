"""Data access for the dashboard: load once, score once, cache everything."""
import socket
import subprocess
import sys

import pandas as pd
import streamlit as st

from config import settings as S
from src.data import load_data
from src.services import prediction_service as svc


def ensure_data():
    """If the processed files are missing, run the data pipeline once."""
    needed = (S.THEFT_PROCESSED, S.TRANSFORMER_PROCESSED, S.AREAS_PROCESSED)
    if all(p.exists() for p in needed):
        return
    with st.spinner("First run: preparing datasets..."):
        subprocess.run([sys.executable, str(S.ROOT / "scripts" / "run_pipeline.py"), "--no-figures"],
                       check=True, cwd=S.ROOT)


@st.cache_data(show_spinner="Loading data and scoring...")
def load_all():
    ensure_data()
    areas = load_data.load_areas()
    theft = load_data.load_theft_processed()
    trf = load_data.load_transformer_processed()

    theft_scores = svc.score_theft(theft)
    theft_full = theft.merge(theft_scores, on=["meter_id", "month"], how="left")

    trf_scores = svc.score_transformers(trf)
    trf_full = trf.merge(trf_scores, on=["transformer_id", "date"], how="left")
    return {"areas": areas, "theft": theft_full, "trf": trf_full}


def apply_filters(theft, trf, f):
    """Filter dict from the sidebar -> filtered copies."""
    t = theft[theft["area"].isin(f["areas"]) & theft["meter_type"].isin(f["meter_types"])]
    x = trf[trf["area"].isin(f["areas"])]
    return t, x


def latest_theft(theft, as_of_month):
    """One row per meter at the chosen month."""
    return theft[theft["month"] == as_of_month]


def latest_trf(trf, as_of_date):
    return trf[trf["date"] == as_of_date]


def area_summary(theft_latest, trf_window, areas):
    """Combine both models into one simple 0-1 area score for the map.

    score = 0.5 * (suspicious share / 25%)  +  0.5 * (mean 7-day failure prob / 15%),
    each part capped at 1. A simple, explainable rule for the exhibition map.
    """
    s = (theft_latest.assign(susp=(theft_latest["label"] == "Suspicious").astype(int))
         .groupby("area").agg(meters=("meter_id", "nunique"), suspicious_meters=("susp", "sum")))
    t = trf_window.groupby("area").agg(avg_fail_prob=("failure_prob_7d", "mean"))
    hi = (trf_window[trf_window["risk_level"] == "High"].groupby("area")["transformer_id"].nunique()
          .rename("high_risk_transformers"))
    out = areas.set_index("area").join(s).join(t).join(hi)
    out[["meters", "suspicious_meters", "high_risk_transformers"]] = \
        out[["meters", "suspicious_meters", "high_risk_transformers"]].fillna(0).astype(int)
    out["avg_fail_prob"] = out["avg_fail_prob"].fillna(0)
    share = (out["suspicious_meters"] / out["meters"].replace(0, pd.NA)).astype(float).fillna(0)
    out["risk_score"] = (0.5 * (share / 0.25).clip(upper=1) + 0.5 * (out["avg_fail_prob"] / 0.15).clip(upper=1)).round(3)
    return out.reset_index()


def peak_in_window(trf, as_of_date, days=30):
    """Each transformer's highest-risk reading in the `days` up to `as_of_date`.

    Used on the overview and map so a calm single day does not hide a week
    of elevated risk.
    """
    w = trf[(trf["date"] <= as_of_date) & (trf["date"] > as_of_date - pd.Timedelta(days=days))]
    return w.sort_values("failure_prob_7d", ascending=False).drop_duplicates("transformer_id")


@st.cache_data(ttl=60, show_spinner=False)
def internet_available():
    """True if map tiles could be downloaded. Folium needs internet; the offline map does not."""
    try:
        socket.create_connection(("tile.openstreetmap.org", 443), timeout=1.5).close()
        return True
    except OSError:
        return False
