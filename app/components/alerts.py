"""Alert cards with a coloured edge."""
import streamlit as st

from config import settings as S


def _card(title, subtitle, body, color):
    st.markdown(
        f"<div style='border-left:5px solid {color};background:#f7f9fb;padding:8px 14px;"
        f"margin-bottom:8px;border-radius:4px'>"
        f"<div style='font-weight:700'>{title} <span style='font-weight:400;color:#5b6773'>· {subtitle}</span></div>"
        f"<div style='font-size:0.9rem;color:#33404d'>{body}</div></div>",
        unsafe_allow_html=True)


def theft_alerts(df, limit=5):
    """df: scored latest-month rows (needs meter_id, area, risk_score, change_pct, recommendation)."""
    top = df[df["label"] == "Suspicious"].sort_values("risk_score", ascending=False).head(limit)
    if top.empty:
        st.success("No suspicious meters for this selection.")
    for r in top.itertuples():
        _card(r.meter_id, f"{r.area} · risk {r.risk_score:.0%} · {r.change_pct:+.0f}% vs last month",
              r.recommendation, S.THEFT_COLORS["Suspicious"])


def transformer_alerts(df, limit=5):
    """df: scored rows; only High / Medium shown, highest probability first."""
    top = df[df["risk_level"].isin(["High", "Medium"])].sort_values("failure_prob_7d", ascending=False).head(limit)
    if top.empty:
        st.success("No elevated transformer risk for this selection.")
    for r in top.itertuples():
        _card(r.transformer_id, f"{r.area} · {r.risk_level} · {r.failure_prob_7d:.0%} 7-day failure risk",
              r.recommendation, S.RISK_COLORS[r.risk_level])
