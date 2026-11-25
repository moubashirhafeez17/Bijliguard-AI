import pandas as pd

BASE_FEATURES = ["capacity_kva", "age_years", "load_pct", "oil_temp_c", "ambient_temp_c", "humidity_pct"]
ENGINEERED_FEATURES = ["load_mean_3d", "load_mean_7d", "oil_mean_3d", "oil_mean_7d", "load_max_7d", "oil_max_7d", "overload_days_7d", "oil_ambient_delta"]
FEATURE_COLUMNS = BASE_FEATURES + ENGINEERED_FEATURES
REQUIRED_COLUMNS = ["transformer_id", "date", *BASE_FEATURES]

def build_transformer_features(df):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required transformer columns: {missing}")
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    if out["date"].isna().any():
        raise ValueError("Column 'date' contains invalid dates.")
    out = out.sort_values(["transformer_id", "date"]).reset_index(drop=True)
    for c in BASE_FEATURES:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    g = out.groupby("transformer_id", sort=False)
    for col, name, win, operation in [
        ("load_pct", "load_mean_3d", 3, "mean"), ("load_pct", "load_mean_7d", 7, "mean"),
        ("oil_temp_c", "oil_mean_3d", 3, "mean"), ("oil_temp_c", "oil_mean_7d", 7, "mean"),
        ("load_pct", "load_max_7d", 7, "max"), ("oil_temp_c", "oil_max_7d", 7, "max")]:
        out[name] = g[col].transform(lambda s: getattr(s.rolling(win, min_periods=1), operation)())
    out["overload_days_7d"] = (out["load_pct"] >= 100).astype(float).groupby(out["transformer_id"]).transform(lambda s: s.rolling(7, min_periods=1).sum())
    out["oil_ambient_delta"] = out["oil_temp_c"] - out["ambient_temp_c"]
    return out
