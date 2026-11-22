"""Generate SYNTHETIC Karachi-style datasets for BijliGuard.

All values are simulated. They demonstrate the workflow; they say nothing about
real K-Electric performance. The raw files are deliberately a little dirty
(missing values, duplicates, inconsistent spellings, sensor glitches) so the
cleaning step has real work to do.

Usage:  python scripts/generate_synthetic_data.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings as S  # noqa: E402

# Approximate monthly mean temperature (deg C) for Karachi, Jan..Dec.
KARACHI_MONTH_TEMP = [19, 21, 25, 29, 31, 32, 30, 29, 29, 28, 24, 20]


def season_factor(temp_c):
    """Air-conditioning effect: more units in hot months (simulated)."""
    return 1 + 0.035 * (np.asarray(temp_c) - 26)


# ====================================================================== theft
def generate_theft(rng, n_meters=800, n_months=12, end_month="2026-10-01"):
    areas = S.AREA_NAMES
    area_w = np.array([3, 3, 2, 4, 3, 3, 3, 3, 2, 3, 4, 2, 1, 1], dtype=float)
    area_w /= area_w.sum()

    meter_area = rng.choice(areas, size=n_meters, p=area_w)
    meter_type = rng.choice(S.METER_TYPES, size=n_meters, p=[0.80, 0.16, 0.04])
    income = np.array([S.AREAS[a][2] for a in meter_area])
    propensity = np.array([S.AREAS[a][3] for a in meter_area])

    type_mult = np.select(
        [meter_type == "Residential", meter_type == "Commercial"], [1.0, 2.6], 8.0
    )
    base_units = rng.lognormal(mean=np.log(300), sigma=0.28, size=n_meters) * income * type_mult

    # Who steals, who is a harmless "decoy" with a temporary valid drop.
    is_thief = rng.random(n_meters) < propensity * 1.1
    is_decoy = (~is_thief) & (rng.random(n_meters) < 0.04)
    gradual = rng.random(n_meters) < 0.30

    total = n_months + 1  # one extra leading month so month 1 has 'previous_units'
    months = pd.date_range(end=end_month, periods=total, freq="MS")
    theft_start = rng.integers(3, total - 1, size=n_meters)  # index of first tampered month
    decoy_start = rng.integers(2, total, size=n_meters)

    rows = []
    for i in range(n_meters):
        for m_idx, month in enumerate(months):
            temp = KARACHI_MONTH_TEMP[month.month - 1] + rng.normal(0, 1.2)
            units = base_units[i] * season_factor(temp) * rng.normal(1.0, 0.07)
            suspicious = 0
            if is_thief[i] and m_idx >= theft_start[i]:
                if gradual[i]:
                    steps = m_idx - theft_start[i] + 1
                    units *= max(0.25, 1 - 0.18 * steps)
                else:
                    units *= rng.uniform(0.20, 0.50)
                suspicious = 1
            elif is_decoy[i] and decoy_start[i] <= m_idx <= decoy_start[i] + 1:
                units *= rng.uniform(0.35, 0.55)  # e.g. family away - NOT theft
            units = max(units, 5.0)

            # Simple simulated tariff (PKR) - slabs differ by meter type.
            if meter_type[i] == "Residential":
                rate = 22 if units <= 200 else 30 if units <= 400 else 38
            elif meter_type[i] == "Commercial":
                rate = 42
            else:
                rate = 36
            bill = units * rate + 250 + rng.normal(0, 40)
            rows.append((f"MTR-{i:05d}", month, meter_area[i], meter_type[i],
                         round(units, 1), round(temp, 1), round(bill, 0), suspicious))

    df = pd.DataFrame(rows, columns=["meter_id", "month", "area", "meter_type",
                                     "monthly_units", "temperature_c",
                                     "bill_amount_pkr", "is_suspicious"])
    df["previous_units"] = df.groupby("meter_id")["monthly_units"].shift(1)
    df = df[df["month"] > months[0]].reset_index(drop=True)
    return df[S.THEFT_COLUMNS]


def make_theft_dirty(df, rng):
    """Inject realistic problems into the raw theft file."""
    df = df.copy()
    n = len(df)
    df["month"] = df["month"].dt.strftime("%Y-%m-%d")

    df.loc[rng.random(n) < 0.02, "monthly_units"] = np.nan
    df.loc[rng.random(n) < 0.015, "temperature_c"] = np.nan
    df.loc[rng.random(n) < 0.01, "bill_amount_pkr"] = np.nan
    df.loc[rng.random(n) < 0.003, "monthly_units"] = -1 * rng.integers(1, 50)  # impossible

    variants = {"DHA": ["dha", " DHA ", "Defence"], "Gulshan-e-Iqbal": ["Gulshan e Iqbal", "gulshan"],
                "Korangi": ["korangi ", "KORANGI"], "Orangi Town": ["Orangi", "orangi town"],
                "North Nazimabad": ["north nazimabad", "N. Nazimabad"]}
    for canon, alts in variants.items():
        hit = (df["area"] == canon) & (rng.random(n) < 0.06)
        df.loc[hit, "area"] = rng.choice(alts, size=int(hit.sum()))
    hit = rng.random(n) < 0.04
    df.loc[hit, "meter_type"] = df.loc[hit, "meter_type"].str.upper()
    hit = rng.random(n) < 0.02
    df.loc[hit, "meter_type"] = df.loc[hit, "meter_type"].str.lower()

    dupes = df.sample(frac=0.01, random_state=int(rng.integers(0, 10_000)))
    return pd.concat([df, dupes], ignore_index=True).sample(frac=1, random_state=1).reset_index(drop=True)


# ================================================================ transformer
def generate_transformer(rng, n_transformers=120, n_days=180, end_date="2026-11-21"):
    areas = S.AREA_NAMES
    t_area = rng.choice(areas, size=n_transformers)
    capacity = rng.choice([100, 200, 315, 500], size=n_transformers, p=[0.25, 0.35, 0.30, 0.10])
    age = rng.integers(2, 31, size=n_transformers)
    # Poorer / denser areas are loaded harder in the simulation.
    base_load = np.array([85 - 22 * (S.AREAS[a][2] - 0.6) for a in t_area]) + rng.normal(0, 6, n_transformers)

    dates = pd.date_range(end=end_date, periods=n_days, freq="D")
    rows = []
    for i in range(n_transformers):
        cooldown = 0
        for d in dates:
            temp = KARACHI_MONTH_TEMP[d.month - 1] + rng.normal(0, 1.8)
            humidity = np.clip(62 + (14 if d.month in (7, 8, 9) else 0) + rng.normal(0, 6), 30, 98)
            load = base_load[i] * (1 + 0.012 * (temp - 28)) + rng.normal(0, 6)
            if rng.random() < 0.02:
                load += rng.uniform(15, 35)  # evening-peak spike
            load = float(np.clip(load, 20, 150))
            oil = temp + 12 + 0.45 * load + rng.normal(0, 2.5)
            rows.append([f"TRF-{i + 1:03d}", d, t_area[i], int(capacity[i]), int(age[i]),
                         round(load, 1), round(oil, 1), round(temp, 1), round(humidity, 1), 0])
    df = pd.DataFrame(rows, columns=["transformer_id", "date", "area", "capacity_kva", "age_years",
                                     "load_pct", "oil_temp_c", "ambient_temp_c", "humidity_pct",
                                     "failed_today"])

    # Failure process: hazard rises with oil temperature, overload streak and age.
    df = df.sort_values(["transformer_id", "date"]).reset_index(drop=True)
    overload = (df["load_pct"] > 95).astype(int)
    grp = (overload != overload.groupby(df["transformer_id"]).shift(1)).cumsum()
    streak = overload.groupby(grp).cumsum() * overload
    z = (-5.9 + 0.075 * (df["oil_temp_c"] - 65) + 0.035 * (df["age_years"] - 15)
         + 0.28 * streak.clip(upper=7))
    p = 1 / (1 + np.exp(-z))
    draws = rng.random(len(df)) < p
    failed = np.zeros(len(df), dtype=int)
    last_idx, last_tid = -100, None
    for idx, (tid, hit) in enumerate(zip(df["transformer_id"].to_numpy(), draws)):
        if tid != last_tid:
            last_tid, last_idx = tid, -100
        if hit and idx - last_idx > 14:  # repaired for ~2 weeks after a failure
            failed[idx] = 1
            last_idx = idx
    df["failed_today"] = failed

    # 7-day-ahead label (NaN in the final 7 days: outcome not yet observed).
    fut = pd.concat([df.groupby("transformer_id")["failed_today"].shift(-k) for k in range(1, 8)], axis=1)
    label = (fut.max(axis=1) > 0).astype("float")
    label[fut.isna().any(axis=1)] = np.nan
    df["failure_next_7d"] = label
    return df[S.TRANSFORMER_COLUMNS]


def make_transformer_dirty(df, rng):
    df = df.copy()
    n = len(df)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df.loc[rng.random(n) < 0.015, "oil_temp_c"] = np.nan
    df.loc[rng.random(n) < 0.010, "humidity_pct"] = np.nan
    df.loc[rng.random(n) < 0.008, "load_pct"] = np.nan
    glitch = rng.random(n) < 0.002
    df.loc[glitch, "oil_temp_c"] = rng.choice([999.0, -1.0, 0.0], size=int(glitch.sum()))
    for canon, alts in {"DHA": ["dha", "Defence"], "Korangi": ["korangi "], "Lyari": ["LYARI"],
                        "SITE": ["site area", "Site"]}.items():
        hit = (df["area"] == canon) & (rng.random(n) < 0.05)
        df.loc[hit, "area"] = rng.choice(alts, size=int(hit.sum()))
    dupes = df.sample(frac=0.005, random_state=int(rng.integers(0, 10_000)))
    return pd.concat([df, dupes], ignore_index=True).sample(frac=1, random_state=2).reset_index(drop=True)


# ======================================================================= main
def main():
    S.SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(S.RANDOM_SEED)

    theft = generate_theft(rng)
    make_theft_dirty(theft, rng).to_csv(S.SYNTH_THEFT_RAW, index=False)

    trf = generate_transformer(rng)
    make_transformer_dirty(trf, rng).to_csv(S.SYNTH_TRANSFORMER_RAW, index=False)

    areas = pd.DataFrame(
        [(n, lat, lon, inc, prop) for n, (lat, lon, inc, prop) in S.AREAS.items()],
        columns=["area", "latitude", "longitude", "income_factor", "theft_propensity"],
    )
    areas.to_csv(S.SYNTH_AREAS, index=False)

    print(f"theft raw:        {len(theft):>7,} clean rows  -> {S.SYNTH_THEFT_RAW.name}")
    print(f"  suspicious rows: {theft['is_suspicious'].mean():.1%}")
    print(f"transformer raw:  {len(trf):>7,} clean rows  -> {S.SYNTH_TRANSFORMER_RAW.name}")
    print(f"  failures: {int(trf['failed_today'].sum())}  | 7-day positive rate: {trf['failure_next_7d'].mean():.1%}")
    print(f"areas:            {len(areas)} -> {S.SYNTH_AREAS.name}")


if __name__ == "__main__":
    main()
