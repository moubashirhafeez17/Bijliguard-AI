"""Quality checks. Return a dict of findings; 'issues' must be empty to pass."""
import pandas as pd

from config import settings as S


def _range_issues(df, issues):
    for col, (lo, hi) in S.VALID_RANGES.items():
        if col in df.columns:
            n = int(((df[col] < lo) | (df[col] > hi)).sum())
            if n:
                issues.append(f"{col}: {n} values outside [{lo}, {hi}]")


def validate_theft(df):
    issues = []
    missing_cols = [c for c in S.THEFT_COLUMNS if c not in df.columns]
    if missing_cols:
        return {"passed": False, "issues": [f"missing columns: {missing_cols}"]}
    nulls = df[S.THEFT_COLUMNS].isna().sum()
    for col, n in nulls[nulls > 0].items():
        issues.append(f"{col}: {int(n)} missing values")
    n_dup = int(df.duplicated(["meter_id", "month"]).sum())
    if n_dup:
        issues.append(f"{n_dup} duplicate meter-month rows")
    bad_area = sorted(set(df["area"]) - set(S.AREA_NAMES))
    if bad_area:
        issues.append(f"unknown areas: {bad_area}")
    bad_type = sorted(set(df["meter_type"]) - set(S.METER_TYPES))
    if bad_type:
        issues.append(f"unknown meter types: {bad_type}")
    _range_issues(df, issues)
    return {
        "passed": not issues,
        "issues": issues,
        "rows": len(df),
        "meters": int(df["meter_id"].nunique()),
        "months": f"{df['month'].min():%Y-%m} to {df['month'].max():%Y-%m}",
        "suspicious_share": round(float(df["is_suspicious"].mean()), 4),
    }


def validate_transformer(df):
    issues = []
    missing_cols = [c for c in S.TRANSFORMER_COLUMNS if c not in df.columns]
    if missing_cols:
        return {"passed": False, "issues": [f"missing columns: {missing_cols}"]}
    feature_cols = [c for c in S.TRANSFORMER_COLUMNS if c != "failure_next_7d"]
    nulls = df[feature_cols].isna().sum()
    for col, n in nulls[nulls > 0].items():
        issues.append(f"{col}: {int(n)} missing values")
    n_dup = int(df.duplicated(["transformer_id", "date"]).sum())
    if n_dup:
        issues.append(f"{n_dup} duplicate transformer-date rows")
    bad_area = sorted(set(df["area"]) - set(S.AREA_NAMES))
    if bad_area:
        issues.append(f"unknown areas: {bad_area}")
    _range_issues(df, issues)
    return {
        "passed": not issues,
        "issues": issues,
        "rows": len(df),
        "transformers": int(df["transformer_id"].nunique()),
        "dates": f"{df['date'].min():%Y-%m-%d} to {df['date'].max():%Y-%m-%d}",
        "failure_events": int(df["failed_today"].sum()),
        "positive_rate_7d": round(float(df["failure_next_7d"].dropna().astype(float).mean()), 4),
    }
