"""Central settings: paths, Karachi areas, column names, thresholds.

Everything that more than one module needs lives here so the data pipeline
and the dashboard always agree on names.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ----------------------------------------------------------------- paths
DATA_DIR = ROOT / "data"
RAW_THEFT_DIR = DATA_DIR / "raw" / "theft"
RAW_TRANSFORMER_DIR = DATA_DIR / "raw" / "transformer"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_THEFT_DIR = DATA_DIR / "processed" / "theft"
PROCESSED_TRANSFORMER_DIR = DATA_DIR / "processed" / "transformer"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DOCS_DIR = ROOT / "docs"

SYNTH_THEFT_RAW = SYNTHETIC_DIR / "theft_raw_synthetic.csv"
SYNTH_TRANSFORMER_RAW = SYNTHETIC_DIR / "transformer_raw_synthetic.csv"
SYNTH_AREAS = SYNTHETIC_DIR / "karachi_areas.csv"

THEFT_PROCESSED = PROCESSED_THEFT_DIR / "theft_clean.csv"
TRANSFORMER_PROCESSED = PROCESSED_TRANSFORMER_DIR / "transformer_clean.csv"
AREAS_PROCESSED = DATA_DIR / "processed" / "karachi_areas.csv"
QUALITY_REPORT = REPORTS_DIR / "data_quality_report.json"

# ----------------------------------------------------------------- areas
# name: (latitude, longitude, income_factor, theft_propensity)
# Coordinates are approximate area centres. Factors are SIMULATED assumptions
# used only to make the synthetic data look plausible - not real statistics.
AREAS = {
    "DHA":               (24.8000, 67.0600, 1.45, 0.02),
    "Clifton":           (24.8130, 67.0300, 1.40, 0.02),
    "Saddar":            (24.8600, 67.0100, 1.00, 0.05),
    "Gulshan-e-Iqbal":   (24.9200, 67.0900, 1.00, 0.05),
    "Gulistan-e-Jauhar": (24.9100, 67.1300, 0.95, 0.06),
    "North Nazimabad":   (24.9400, 67.0400, 0.95, 0.05),
    "Malir":             (24.8900, 67.1900, 0.80, 0.09),
    "Korangi":           (24.8300, 67.1300, 0.75, 0.12),
    "Landhi":            (24.8500, 67.2100, 0.70, 0.13),
    "Lyari":             (24.8700, 66.9900, 0.65, 0.16),
    "Orangi Town":       (24.9500, 66.9900, 0.60, 0.17),
    "Surjani Town":      (25.0300, 67.0500, 0.60, 0.15),
    "SITE":              (24.8960, 66.9800, 0.85, 0.08),
    "Bin Qasim":         (24.7900, 67.3400, 0.80, 0.09),
}
AREA_NAMES = list(AREAS)


def _norm(text: str) -> str:
    return "".join(ch for ch in str(text).lower() if ch.isalnum())


# "gulshan e iqbal", " DHA ", "GULSHAN-E-IQBAL" ... all map to the canonical name
AREA_ALIASES = {_norm(name): name for name in AREAS}
AREA_ALIASES.update({
    "defence": "DHA", "dhakarachi": "DHA", "gulshan": "Gulshan-e-Iqbal",
    "jauhar": "Gulistan-e-Jauhar", "orangi": "Orangi Town",
    "surjani": "Surjani Town", "binqasim": "Bin Qasim", "sitearea": "SITE",
    "nnazimabad": "North Nazimabad", "site": "SITE",
})


def canonical_area(value):
    """Return the canonical area name, or None if it is not recognised."""
    return AREA_ALIASES.get(_norm(value))


# ----------------------------------------------------------------- columns
METER_TYPES = ["Residential", "Commercial", "Industrial"]

THEFT_COLUMNS = [
    "meter_id", "month", "area", "meter_type", "monthly_units",
    "previous_units", "bill_amount_pkr", "temperature_c", "is_suspicious",
]
TRANSFORMER_COLUMNS = [
    "transformer_id", "date", "area", "capacity_kva", "age_years",
    "load_pct", "oil_temp_c", "ambient_temp_c", "humidity_pct",
    "failed_today", "failure_next_7d",
]

# Physically plausible ranges used by validation and cleaning.
VALID_RANGES = {
    "monthly_units": (0, 20000),
    "previous_units": (0, 20000),
    "bill_amount_pkr": (0, 2_000_000),
    "temperature_c": (5, 50),
    "load_pct": (0, 200),
    "oil_temp_c": (10, 130),
    "ambient_temp_c": (5, 50),
    "humidity_pct": (0, 100),
    "capacity_kva": (25, 2000),
    "age_years": (0, 60),
}

# ----------------------------------------------------------------- display
RISK_COLORS = {"Low": "#2a9d8f", "Medium": "#e9a23b", "High": "#d1495b"}
THEFT_COLORS = {"Normal": "#2a9d8f", "Suspicious": "#d1495b"}
RANDOM_SEED = 42
