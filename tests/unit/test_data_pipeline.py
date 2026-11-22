import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import settings as S  # noqa: E402
from src.data import clean_data, validate_data  # noqa: E402
from src.services import prediction_service as svc  # noqa: E402


def _theft_raw():
    return pd.DataFrame({
        "meter_id": ["M1", "M1", "M1", "M2", "M2", "M2", "M2"],
        "month": ["2026-01-01", "2026-02-01", "2026-02-01", "2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01"],
        "area": [" dha", "DHA", "DHA", "gulshan e iqbal", "Gulshan-e-Iqbal", "Nowhere", "Korangi "],
        "meter_type": ["RESIDENTIAL", "residential", "residential", "Commercial", "Commercial", "Commercial", "Commercial"],
        "monthly_units": [300, np.nan, 280, 800, -5, 790, 810],
        "previous_units": [310, 300, 300, 790, 800, 800, 790],
        "bill_amount_pkr": [9000, 8500, 8500, 30000, 31000, np.nan, 30500],
        "temperature_c": [20, np.nan, 22, 20, 22, 25, 29],
        "is_suspicious": [0, 0, 0, 0, 0, 0, 0],
    })


def test_theft_cleaning_fixes_problems():
    clean, rep = clean_data.clean_theft(_theft_raw())
    assert rep["duplicates_removed"] == 1
    assert rep["unrecognised_area_rows_dropped"] == 1
    assert set(clean["area"]) <= set(S.AREA_NAMES)
    assert set(clean["meter_type"]) <= set(S.METER_TYPES)
    assert clean["monthly_units"].min() >= 0
    assert clean.isna().sum().sum() == 0
    assert validate_data.validate_theft(clean)["passed"]


def test_area_aliases():
    assert S.canonical_area("gulshan e iqbal") == "Gulshan-e-Iqbal"
    assert S.canonical_area(" DHA ") == "DHA"
    assert S.canonical_area("N. Nazimabad") == "North Nazimabad"
    assert S.canonical_area("Mars") is None


def test_transformer_cleaning_handles_glitches():
    raw = pd.DataFrame({
        "transformer_id": ["T1"] * 4,
        "date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-03"],
        "area": ["dha", "DHA", "DHA", "DHA"],
        "capacity_kva": [200] * 4, "age_years": [10] * 4,
        "load_pct": [80, np.nan, 85, 85], "oil_temp_c": [70, 999, 72, 72],
        "ambient_temp_c": [25] * 4, "humidity_pct": [60] * 4,
        "failed_today": [0] * 4, "failure_next_7d": [0, 0, np.nan, np.nan],
    })
    clean, rep = clean_data.clean_transformer(raw)
    assert rep["sensor_glitches_set_missing"] == 1
    assert len(clean) == 3
    assert clean["oil_temp_c"].between(10, 130).all()
    assert validate_data.validate_transformer(clean)["passed"]


def test_single_meter_prediction_sensible():
    drop = svc.predict_single_meter(90, 340, 30, usual_units=350)
    same = svc.predict_single_meter(340, 345, 30, usual_units=350)
    assert drop["label"] == "Suspicious" and same["label"] == "Normal"


def test_single_transformer_risk_increases_with_stress():
    low = svc.predict_single_transformer(60, 65, 5, 0)
    high = svc.predict_single_transformer(120, 100, 25, 6)
    assert high["failure_prob_7d"] > low["failure_prob_7d"]
    assert high["risk_level"] == "High" and low["risk_level"] == "Low"
