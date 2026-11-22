# BijliGuard Data Dictionary

**Data origin:** every value in the current files is **SIMULATED**. No real K-Electric
data is used. The synthetic generator is `scripts/generate_synthetic_data.py`.
If a public dataset is placed in `data/raw/theft/` or `data/raw/transformer/`,
the loader uses it instead (its columns must be mapped to the names below).

| Dataset | File | Origin |
|---|---|---|
| Theft (cleaned) | `data/processed/theft/theft_clean.csv` | Simulated |
| Transformer (cleaned) | `data/processed/transformer/transformer_clean.csv` | Simulated |
| Karachi areas | `data/processed/karachi_areas.csv` | Approximate area centres; factors simulated |
| Raw (dirty) copies | `data/synthetic/*_raw_synthetic.csv` | Simulated, with deliberate errors |

## 1. Theft dataset (one row per meter per month)

| Column | Type | Description | Origin |
|---|---|---|---|
| `meter_id` | text | Meter identifier, `MTR-00000` format | Simulated |
| `month` | date | First day of the billing month | Simulated |
| `area` | text | One of 14 Karachi areas (canonical spelling) | Simulated |
| `meter_type` | text | `Residential`, `Commercial` or `Industrial` | Simulated |
| `monthly_units` | number | Electricity consumed that month (kWh) | Simulated |
| `previous_units` | number | Previous month's units for the same meter | Derived |
| `bill_amount_pkr` | number | Bill in PKR from a simple simulated tariff | Simulated |
| `temperature_c` | number | Average temperature that month (°C) | Simulated, Karachi-like seasonality |
| `is_suspicious` | 0/1 | Simulated ground truth: reading follows simulated tampering | Simulated label |

Notes: a few meters have a temporary valid drop (e.g. family away) labelled 0, so
that "low consumption is not always theft" is visible in the data.

## 2. Transformer dataset (one row per transformer per day)

| Column | Type | Description | Origin |
|---|---|---|---|
| `transformer_id` | text | `TRF-001` format | Simulated |
| `date` | date | Reading date | Simulated |
| `area` | text | Karachi area | Simulated |
| `capacity_kva` | integer | Rated capacity: 100, 200, 315 or 500 | Simulated |
| `age_years` | integer | Age of the transformer | Simulated |
| `load_pct` | number | Load as % of rated capacity | Simulated |
| `oil_temp_c` | number | Oil temperature (°C) | Simulated, rises with load and ambient temperature |
| `ambient_temp_c` | number | Outside temperature (°C) | Simulated |
| `humidity_pct` | number | Relative humidity (%) | Simulated |
| `failed_today` | 0/1 | A failure was simulated on this day | Simulated label |
| `failure_next_7d` | 0/1 or empty | 1 if a failure occurs in the next 7 days. **Empty for the last 7 days** (outcome not yet known) | Simulated label |

## 3. Areas dataset

| Column | Description |
|---|---|
| `area` | Canonical area name |
| `latitude`, `longitude` | Approximate centre of the area |
| `income_factor` | Simulated multiplier on typical consumption |
| `theft_propensity` | Simulated share of meters with theft |

## 4. Cleaning rules applied (`src/data/clean_data.py`)

- Dates parsed; rows with unreadable dates dropped.
- Duplicate meter-month / transformer-date rows removed (first kept).
- Area spellings standardised (e.g. `gulshan e iqbal` → `Gulshan-e-Iqbal`); unknown areas dropped.
- Meter type casing standardised.
- Impossible values (negative units, oil temp 999 or 0, humidity above 100) set to missing.
- Missing values filled: units by the meter's own median, temperature by the month's median,
  bill by the meter's usual PKR per unit, transformer sensors by interpolation within the same transformer.
- `previous_units` rebuilt from the sorted series so it matches repaired values.
- A count of every change is saved in `reports/data_quality_report.json`.

## 5. Known limitations

- Simulated data shows the workflow only. It cannot prove real-world accuracy.
- Because the simulation follows simple rules, any model trained on it will look better than it would on real data.
