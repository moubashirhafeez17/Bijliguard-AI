"""Static (matplotlib) exploratory charts saved to reports/figures/.

These are the "understand the data" charts for the report. The interactive
Plotly versions used by the dashboard live in app/components/charts.py.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from config import settings as S  # noqa: E402

NORMAL, SUSP, NEUTRAL = "#2a9d8f", "#d1495b", "#4a6fa5"


def _style(ax, title, xlabel="", ylabel=""):
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)


def _save(fig, name):
    S.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = S.FIGURES_DIR / name
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ---------------------------------------------------------------- theft
def theft_units_distribution(theft):
    fig, ax = plt.subplots(figsize=(7, 4))
    bins = np.linspace(0, theft["monthly_units"].quantile(0.99), 40)
    ax.hist(theft.loc[theft.is_suspicious == 0, "monthly_units"], bins=bins, alpha=0.75,
            color=NORMAL, label="Normal", density=True)
    ax.hist(theft.loc[theft.is_suspicious == 1, "monthly_units"], bins=bins, alpha=0.75,
            color=SUSP, label="Suspicious", density=True)
    _style(ax, "Monthly units: normal vs suspicious (simulated)", "Monthly units (kWh)", "Density")
    ax.legend(frameon=False)
    return _save(fig, "theft_units_distribution.png")


def theft_monthly_trend(theft):
    res = theft[theft.meter_type == "Residential"]
    g = res.groupby([res.month, res.is_suspicious])["monthly_units"].mean().unstack()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(g.index, g[0], color=NORMAL, marker="o", label="Normal meters")
    if 1 in g:
        ax.plot(g.index, g[1], color=SUSP, marker="o", label="Suspicious readings")
    _style(ax, "Average residential consumption by month", "", "Average units (kWh)")
    ax.legend(frameon=False)
    fig.autofmt_xdate()
    return _save(fig, "theft_monthly_trend.png")


def theft_suspicious_by_area(theft):
    rate = theft.groupby("area")["is_suspicious"].mean().sort_values() * 100
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(rate.index, rate.values, color=NEUTRAL)
    _style(ax, "Share of suspicious meter-months by area (simulated)", "% of readings")
    ax.grid(axis="x", alpha=0.25)
    ax.grid(axis="y", visible=False)
    return _save(fig, "theft_suspicious_by_area.png")


def theft_temperature_vs_units(theft):
    res = theft[(theft.meter_type == "Residential") & (theft.is_suspicious == 0)]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.scatter(res.temperature_c, res.monthly_units, s=6, alpha=0.25, color=NEUTRAL)
    _style(ax, "Temperature vs units (normal residential)", "Temperature (°C)", "Monthly units (kWh)")
    return _save(fig, "theft_temperature_vs_units.png")


def theft_by_meter_type(theft):
    fig, ax = plt.subplots(figsize=(7, 4))
    data = [theft.loc[theft.meter_type == t, "monthly_units"] for t in S.METER_TYPES]
    ax.boxplot(data, tick_labels=S.METER_TYPES, showfliers=False)
    ax.set_yscale("log")
    _style(ax, "Consumption by meter type (log scale)", "", "Monthly units (kWh)")
    return _save(fig, "theft_by_meter_type.png")


# ---------------------------------------------------------- transformer
def trf_load_vs_oil(trf):
    d = trf.dropna(subset=["failure_next_7d"]).sample(min(6000, len(trf)), random_state=1)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    neg, pos = d[d.failure_next_7d == 0], d[d.failure_next_7d == 1]
    ax.scatter(neg.load_pct, neg.oil_temp_c, s=6, alpha=0.2, color=NORMAL, label="No failure in 7 days")
    ax.scatter(pos.load_pct, pos.oil_temp_c, s=14, alpha=0.8, color=SUSP, label="Failure within 7 days")
    _style(ax, "Load vs oil temperature (simulated)", "Load (% of capacity)", "Oil temperature (°C)")
    ax.legend(frameon=False)
    return _save(fig, "transformer_load_vs_oil_temp.png")


def trf_failure_by_area(trf):
    rate = trf.dropna(subset=["failure_next_7d"]).groupby("area")["failure_next_7d"].mean().sort_values() * 100
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(rate.index, rate.values, color=NEUTRAL)
    _style(ax, "7-day failure rate by area (simulated)", "% of transformer-days")
    ax.grid(axis="x", alpha=0.25)
    ax.grid(axis="y", visible=False)
    return _save(fig, "transformer_failure_by_area.png")


def trf_age_vs_failures(trf):
    d = trf.dropna(subset=["failure_next_7d"]).copy()
    d["age_band"] = np.select([d.age_years < 10, d.age_years < 20], ["0-9 yrs", "10-19 yrs"], "20+ yrs")
    rate = d.groupby("age_band")["failure_next_7d"].mean().reindex(["0-9 yrs", "10-19 yrs", "20+ yrs"]) * 100
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(rate.index, rate.values, color=NEUTRAL)
    _style(ax, "7-day failure rate by transformer age", "", "% of transformer-days")
    return _save(fig, "transformer_failure_by_age.png")


def trf_correlation(trf):
    cols = ["load_pct", "oil_temp_c", "ambient_temp_c", "humidity_pct", "age_years", "failure_next_7d"]
    d = trf[cols].dropna().astype(float)
    corr = d.corr()
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols)), cols, rotation=40, ha="right")
    ax.set_yticks(range(len(cols)), cols)
    for i in range(len(cols)):
        for j in range(len(cols)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    ax.set_title("Correlation of transformer variables", fontsize=12, fontweight="bold", loc="left")
    fig.colorbar(im, ax=ax, shrink=0.8)
    return _save(fig, "transformer_correlation.png")


def make_all_figures(theft, trf):
    funcs = [(theft_units_distribution, theft), (theft_monthly_trend, theft),
             (theft_suspicious_by_area, theft), (theft_temperature_vs_units, theft),
             (theft_by_meter_type, theft), (trf_load_vs_oil, trf),
             (trf_failure_by_area, trf), (trf_age_vs_failures, trf), (trf_correlation, trf)]
    return [f(d) for f, d in funcs]
