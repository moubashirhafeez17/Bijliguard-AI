"""Folium map of simulated area-wise risk for Karachi."""
import folium

from config import settings as S

KARACHI_CENTER = (24.90, 67.08)


def risk_level_from_score(score):
    return "High" if score >= 0.6 else "Medium" if score >= 0.3 else "Low"


def build_offline_figure(area_df):
    """Plotly bubble map that needs NO internet (Folium/Leaflet loads scripts and
    tiles from the web, so it is blank without a connection).

    Plain longitude/latitude axes with a correction so shapes are not stretched.
    """
    import math

    import plotly.graph_objects as go

    d = area_df.sort_values("risk_score")
    levels = d["risk_score"].map(risk_level_from_score)
    fig = go.Figure(go.Scatter(
        x=d["longitude"], y=d["latitude"], mode="markers+text", text=d["area"], textposition=["top center" if i % 2 else "bottom center" for i in range(len(d))],
        textfont=dict(size=11, color="#33404d"),
        marker=dict(size=14 + 46 * d["risk_score"], color=[S.RISK_COLORS[l] for l in levels],
                    opacity=0.65, line=dict(width=1.5, color="white")),
        customdata=list(zip(levels, d["risk_score"], d.get("suspicious_meters", 0), d.get("high_risk_transformers", 0))),
        hovertemplate="<b>%{text}</b><br>Risk: %{customdata[0]} (%{customdata[1]:.0%})"
                      "<br>Suspicious meters: %{customdata[2]}"
                      "<br>High-risk transformers: %{customdata[3]}<extra></extra>"))
    fig.update_xaxes(visible=False, range=[66.90, 67.42])
    fig.update_yaxes(visible=False, range=[24.72, 25.08],
                     scaleanchor="x", scaleratio=1 / math.cos(math.radians(KARACHI_CENTER[0])))
    fig.add_annotation(x=66.93, y=24.74, text="Arabian Sea ↓", showarrow=False, font=dict(color="#7a8794"))
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="#eef2f5",
                      paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
    return fig


def build_map(area_df, offline=False):
    """area_df columns: area, latitude, longitude, risk_score (0-1), plus optional
    suspicious_meters, high_risk_transformers.

    offline=True draws no web tiles, so the map still works with no internet
    (circles on a plain background) - this is the exhibition-safe mode.
    """
    m = folium.Map(location=KARACHI_CENTER, zoom_start=11, tiles=None if offline else "OpenStreetMap",
                   control_scale=True)
    if offline:
        m.get_root().header.add_child(folium.Element(
            "<style>.leaflet-container{background:#eef2f5}</style>"))

    for r in area_df.itertuples():
        level = risk_level_from_score(r.risk_score)
        color = S.RISK_COLORS[level]
        popup = (f"<b>{r.area}</b><br>Risk: {level} ({r.risk_score:.0%})"
                 f"<br>Suspicious meters: {getattr(r, 'suspicious_meters', 'n/a')}"
                 f"<br>High-risk transformers: {getattr(r, 'high_risk_transformers', 'n/a')}")
        folium.CircleMarker(
            location=(r.latitude, r.longitude),
            radius=9 + 22 * float(r.risk_score),
            color=color, weight=2, fill=True, fill_color=color, fill_opacity=0.55,
            tooltip=f"{r.area} - {level}", popup=folium.Popup(popup, max_width=240),
        ).add_to(m)
        folium.Marker(
            (r.latitude, r.longitude),
            icon=folium.DivIcon(html=f"<div style='font-size:10px;font-weight:600;color:#333;"
                                     f"white-space:nowrap;transform:translate(-50%,14px)'>{r.area}</div>"),
        ).add_to(m)
    return m
