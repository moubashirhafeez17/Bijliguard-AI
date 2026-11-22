"""Interactive Plotly charts for the dashboard."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import settings as S

GRID = "rgba(0,0,0,0.08)"


def _layout(fig, height=340, title=None):
    fig.update_layout(
        height=height, title=dict(text=title, x=0, font=dict(size=15)) if title else None,
        margin=dict(l=10, r=10, t=45 if title else 15, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.18, x=0),
        font=dict(family="sans-serif", size=12),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor=GRID)
    return fig


# ----------------------------------------------------------------- overview
def flagged_by_month(theft):
    g = (theft.assign(s=(theft["label"] == "Suspicious").astype(int))
         .groupby("month")["s"].sum().reset_index())
    fig = go.Figure(go.Bar(x=g["month"], y=g["s"], marker_color=S.THEFT_COLORS["Suspicious"]))
    fig.update_yaxes(title="Suspicious meters")
    return _layout(fig, title="Suspicious meters per billing month")


def area_risk_bar(area_df):
    d = area_df.sort_values("risk_score")
    colors = [S.RISK_COLORS["High" if v >= 0.6 else "Medium" if v >= 0.3 else "Low"] for v in d["risk_score"]]
    fig = go.Figure(go.Bar(x=d["risk_score"], y=d["area"], orientation="h", marker_color=colors,
                           hovertemplate="%{y}: %{x:.0%}<extra></extra>"))
    fig.update_xaxes(range=[0, 1], tickformat=".0%", gridcolor=GRID)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    return _layout(fig, height=420, title="Combined area risk score")


def risk_donut(latest_trf, title="Transformers by risk level"):
    counts = latest_trf["risk_level"].value_counts().reindex(["Low", "Medium", "High"]).fillna(0)
    fig = go.Figure(go.Pie(labels=counts.index, values=counts.values, hole=0.6, sort=False,
                           marker_colors=[S.RISK_COLORS[k] for k in counts.index], textinfo="label+value"))
    fig.update_layout(showlegend=False)
    return _layout(fig, height=300, title=title)


# -------------------------------------------------------------------- theft
def meter_timeline(m):
    """m: one meter's rows sorted by month (needs monthly_units, label, risk_score)."""
    baseline = m["monthly_units"].quantile(0.75)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=m["month"], y=m["monthly_units"], mode="lines+markers", name="Monthly units",
                             line=dict(color="#4a6fa5", width=2)))
    flag = m[m["label"] == "Suspicious"]
    if len(flag):
        fig.add_trace(go.Scatter(x=flag["month"], y=flag["monthly_units"], mode="markers", name="Flagged",
                                 marker=dict(color=S.THEFT_COLORS["Suspicious"], size=13, symbol="x"),
                                 customdata=flag["risk_score"],
                                 hovertemplate="%{x|%b %Y}: %{y:,.0f} kWh<br>risk %{customdata:.0%}<extra>Flagged</extra>"))
    fig.add_hline(y=baseline, line_dash="dot", line_color="#8a96a3",
                  annotation_text="usual level (75th percentile)", annotation_position="top left")
    fig.update_yaxes(title="kWh", rangemode="tozero")
    return _layout(fig, title="Consumption history")


def theft_risk_hist(latest):
    fig = go.Figure(go.Histogram(x=latest["risk_score"], nbinsx=20, marker_color="#4a6fa5"))
    fig.update_xaxes(title="Risk score", tickformat=".0%")
    fig.update_yaxes(title="Meters")
    return _layout(fig, height=300, title="Distribution of meter risk scores")


# -------------------------------------------------------------- transformer
def transformer_series(t):
    """t: one transformer's rows sorted by date."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=t["date"], y=t["load_pct"], name="Load (%)", line=dict(color="#4a6fa5")), secondary_y=False)
    fig.add_trace(go.Scatter(x=t["date"], y=t["oil_temp_c"], name="Oil temp (°C)", line=dict(color="#e9a23b")), secondary_y=True)
    fig.add_hline(y=100, line_dash="dot", line_color="#d1495b", annotation_text="100% load", secondary_y=False)
    fig.update_yaxes(title_text="Load (% of capacity)", range=[30, 150], dtick=20, secondary_y=False)
    fig.update_yaxes(title_text="Oil temperature (°C)", range=[50, 110], dtick=10, secondary_y=True, showgrid=False)
    return _layout(fig, title="Load and oil temperature")


def risk_trend(t):
    fig = go.Figure(go.Scatter(x=t["date"], y=t["failure_prob_7d"], fill="tozeroy",
                               line=dict(color=S.RISK_COLORS["High"]), name="7-day failure probability"))
    fig.add_hline(y=0.30, line_dash="dot", line_color="#8a96a3", annotation_text="High threshold")
    fig.update_yaxes(tickformat=".0%", rangemode="tozero")
    return _layout(fig, height=260, title="Estimated 7-day failure probability")


def risk_gauge(prob, level):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=prob * 100, number={"suffix": "%", "font": {"size": 40}},
        gauge={"axis": {"range": [0, 60]}, "bar": {"color": S.RISK_COLORS[level]},
               "steps": [{"range": [0, 15], "color": "#e3f3f0"},
                         {"range": [15, 30], "color": "#fbf0dc"},
                         {"range": [30, 60], "color": "#f7e0e4"}]}))
    return _layout(fig, height=230)
