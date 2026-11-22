"""Cleaning steps for the theft and transformer datasets.

Each function returns (clean_dataframe, report_dict). The report counts what
was changed so the work is documented, not silent.
"""
import numpy as np
import pandas as pd

from config import settings as S


def _standardise_area(df, report):
    mapped = df["area"].map(S.canonical_area)
    report["unrecognised_area_rows_dropped"] = int(mapped.isna().sum())
    report["area_spellings_fixed"] = int(((mapped != df["area"]) & mapped.notna()).sum())
    df = df.assign(area=mapped).dropna(subset=["area"])
    return df


def clean_theft(raw):
    r = {"rows_in": len(raw)}
    df = raw.copy()

    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    r["bad_dates_dropped"] = int(df["month"].isna().sum())
    df = df.dropna(subset=["month", "meter_id"])

    r["duplicates_removed"] = int(df.duplicated(["meter_id", "month"]).sum())
    df = df.drop_duplicates(["meter_id", "month"], keep="first")

    df = _standardise_area(df, r)
    df["meter_type"] = df["meter_type"].astype(str).str.strip().str.title()
    df = df[df["meter_type"].isin(S.METER_TYPES)]

    # Impossible values -> missing, then fill.
    lo, hi = S.VALID_RANGES["monthly_units"]
    bad = (df["monthly_units"] < lo) | (df["monthly_units"] > hi)
    r["invalid_units_set_missing"] = int(bad.sum())
    df.loc[bad, "monthly_units"] = np.nan

    df = df.sort_values(["meter_id", "month"]).reset_index(drop=True)

    r["missing_units_filled"] = int(df["monthly_units"].isna().sum())
    # Fill with the meter's own median (keeps each meter's scale).
    df["monthly_units"] = df["monthly_units"].fillna(df.groupby("meter_id")["monthly_units"].transform("median"))

    r["missing_temperature_filled"] = int(df["temperature_c"].isna().sum())
    month_temp = df.groupby(df["month"].dt.month)["temperature_c"].transform("median")
    df["temperature_c"] = df["temperature_c"].fillna(month_temp)

    # Bill amount: estimate from the meter's typical PKR-per-unit rate.
    r["missing_bill_filled"] = int(df["bill_amount_pkr"].isna().sum())
    rate = (df["bill_amount_pkr"] / df["monthly_units"]).groupby(df["meter_id"]).transform("median")
    df["bill_amount_pkr"] = df["bill_amount_pkr"].fillna((df["monthly_units"] * rate).round(0))

    # previous_units: rebuild from the sorted series so it stays consistent
    # with any units we just repaired.
    prev = df.groupby("meter_id")["monthly_units"].shift(1)
    r["previous_units_rebuilt"] = int((prev.notna() & ((prev - df["previous_units"]).abs() > 0.05)).sum())
    df["previous_units"] = prev.fillna(df["previous_units"])
    df = df.dropna(subset=["previous_units", "monthly_units"])

    df["monthly_units"] = df["monthly_units"].round(1)
    df["previous_units"] = df["previous_units"].round(1)
    df["is_suspicious"] = df["is_suspicious"].fillna(0).astype(int)

    r["rows_out"] = len(df)
    return df[S.THEFT_COLUMNS].reset_index(drop=True), r


def clean_transformer(raw):
    r = {"rows_in": len(raw)}
    df = raw.copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    r["bad_dates_dropped"] = int(df["date"].isna().sum())
    df = df.dropna(subset=["date", "transformer_id"])

    r["duplicates_removed"] = int(df.duplicated(["transformer_id", "date"]).sum())
    df = df.drop_duplicates(["transformer_id", "date"], keep="first")

    df = _standardise_area(df, r)

    # Sensor glitches (e.g. oil temp 999 or 0) -> missing, then fill in time order.
    sensor_cols = ["load_pct", "oil_temp_c", "ambient_temp_c", "humidity_pct"]
    glitches = 0
    for col in sensor_cols:
        lo, hi = S.VALID_RANGES[col]
        bad = df[col].notna() & ((df[col] <= 0) | (df[col] < lo) | (df[col] > hi))
        glitches += int(bad.sum())
        df.loc[bad, col] = np.nan
    r["sensor_glitches_set_missing"] = glitches

    df = df.sort_values(["transformer_id", "date"]).reset_index(drop=True)
    r["missing_sensor_values_filled"] = int(df[sensor_cols].isna().sum().sum())
    for col in sensor_cols:
        # Interpolate within a transformer's own time series; edges use nearest.
        df[col] = df.groupby("transformer_id")[col].transform(
            lambda s: s.interpolate(limit_direction="both"))
        df[col] = df[col].fillna(df[col].median())

    df["failed_today"] = df["failed_today"].fillna(0).astype(int)
    # Label stays NaN where the 7-day outcome is not yet observed.
    r["rows_without_label_last_7_days"] = int(df["failure_next_7d"].isna().sum())
    df["failure_next_7d"] = df["failure_next_7d"].astype("Int64")

    for col in sensor_cols:
        df[col] = df[col].round(1)

    r["rows_out"] = len(df)
    return df[S.TRANSFORMER_COLUMNS].reset_index(drop=True), r
