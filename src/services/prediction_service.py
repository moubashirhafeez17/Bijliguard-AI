"""The ONE place the dashboard gets predictions from.

The dashboard never imports models directly. When the AI members' trained
models are ready, they plug in here (see `_try_real_*`). Until then, simple
rule-based PLACEHOLDER scores keep the dashboard fully working, and every
result carries a `source` column so the screen can say honestly which is which.

Output contract (also in docs/integration_contract.md)
------------------------------------------------------
Theft, one row per meter-month:
    meter_id, month, label ('Normal'|'Suspicious'), risk_score (0-1),
    change_pct, recommendation, source
Transformer, one row per transformer-date:
    transformer_id, date, risk_level ('Low'|'Medium'|'High'),
    failure_prob_7d (0-1), recommendation, source
"""
import numpy as np
import pandas as pd

SOURCE_MOCK = "placeholder (rule-based)"


# ------------------------------------------------------------------ theft
def _try_real_theft(df):
    try:
        from src.models.theft_detection.predict import predict_theft_batch  # type: ignore
    except Exception:
        return None
    try:
        return predict_theft_batch(df)
    except Exception:
        return None


def _season_adjust(units, temp_c):
    return units / (1 + 0.035 * (temp_c - 26))


def _theft_recommendation(label, risk):
    if label == "Suspicious" and risk >= 0.8:
        return "Priority inspection: large, sustained drop versus this meter's usual pattern."
    if label == "Suspicious":
        return "Schedule an inspection and check for a valid reason (vacancy, repair, solar)."
    if risk >= 0.25:
        return "Watch: consumption is lower than usual. No action yet."
    return "No action needed."


def score_theft(df):
    """Score every meter-month in `df` (processed theft data)."""
    real = _try_real_theft(df)
    if real is not None:
        return real

    d = df.sort_values(["meter_id", "month"]).copy()
    d["adj"] = _season_adjust(d["monthly_units"], d["temperature_c"])
    baseline = d.groupby("meter_id")["adj"].transform(lambda s: s.quantile(0.75))
    ratio = (d["adj"] / baseline).clip(0, 2)
    d["risk_score"] = ((0.80 - ratio) / 0.40).clip(0, 1).round(3)
    d["label"] = np.where(d["risk_score"] >= 0.5, "Suspicious", "Normal")
    d["change_pct"] = ((d["monthly_units"] / d["previous_units"].replace(0, np.nan)) - 1).mul(100).round(1)
    d["recommendation"] = [_theft_recommendation(l, r) for l, r in zip(d["label"], d["risk_score"])]
    d["source"] = SOURCE_MOCK
    return d[["meter_id", "month", "label", "risk_score", "change_pct", "recommendation", "source"]]


def predict_single_meter(monthly_units, previous_units, temperature_c, usual_units=None):
    """Used by the 'try a reading' form. usual_units = the meter's typical level."""
    usual = usual_units if usual_units else previous_units
    adj_ratio = _season_adjust(monthly_units, temperature_c) / max(_season_adjust(usual, temperature_c), 1)
    risk = float(np.clip((0.80 - adj_ratio) / 0.40, 0, 1))
    label = "Suspicious" if risk >= 0.5 else "Normal"
    return {"label": label, "risk_score": round(risk, 3),
            "change_pct": round((monthly_units / max(previous_units, 1) - 1) * 100, 1),
            "recommendation": _theft_recommendation(label, risk), "source": SOURCE_MOCK}


# ------------------------------------------------------------ transformer
def _try_real_transformer(df):
    try:
        from src.models.transformer_prediction.predict import predict_transformer_batch  # type: ignore
    except Exception:
        return None
    try:
        return predict_transformer_batch(df)
    except Exception:
        return None


def _risk_level(p):
    return "High" if p >= 0.30 else "Medium" if p >= 0.15 else "Low"


def _trf_recommendation(level, load, oil):
    if level == "High":
        return (f"Inspect within 48 hours: load {load:.0f}% and oil {oil:.0f}°C. "
                "Consider load transfer or a cooling check.")
    if level == "Medium":
        return "Schedule a routine check this week and keep watching the load."
    return "Normal operation."


def score_transformers(df):
    real = _try_real_transformer(df)
    if real is not None:
        return real

    d = df.sort_values(["transformer_id", "date"]).copy()
    g = d.groupby("transformer_id")
    d["load_3d"] = g["load_pct"].transform(lambda s: s.rolling(3, min_periods=1).mean())
    d["oil_3d"] = g["oil_temp_c"].transform(lambda s: s.rolling(3, min_periods=1).mean())
    over = (d["load_pct"] > 95).astype(int)
    grp = (over != over.groupby(d["transformer_id"]).shift(1)).cumsum()
    d["streak"] = (over.groupby(grp).cumsum() * over).clip(upper=7)

    z = (-3.6 + 0.07 * (d["oil_3d"] - 65) + 0.02 * (d["load_3d"] - 80)
         + 0.03 * (d["age_years"] - 15) + 0.25 * d["streak"])
    d["failure_prob_7d"] = (1 / (1 + np.exp(-z))).round(3)
    d["risk_level"] = d["failure_prob_7d"].map(_risk_level)
    d["recommendation"] = [_trf_recommendation(l, a, b) for l, a, b in
                           zip(d["risk_level"], d["load_pct"], d["oil_temp_c"])]
    d["source"] = SOURCE_MOCK
    return d[["transformer_id", "date", "risk_level", "failure_prob_7d", "recommendation", "source"]]


def predict_single_transformer(load_pct, oil_temp_c, age_years, overload_days=0):
    z = -3.6 + 0.07 * (oil_temp_c - 65) + 0.02 * (load_pct - 80) + 0.03 * (age_years - 15) + 0.25 * min(overload_days, 7)
    p = float(1 / (1 + np.exp(-z)))
    level = _risk_level(p)
    return {"risk_level": level, "failure_prob_7d": round(p, 3),
            "recommendation": _trf_recommendation(level, load_pct, oil_temp_c), "source": SOURCE_MOCK}
