# Integration Contract

The dashboard only talks to `src/services/prediction_service.py`. Until the trained
models exist, that file returns clearly labelled placeholder scores (`source` column).

## How real models plug in

Add these functions and the service will use them automatically:

- `src/models/theft_detection/predict.py` → `predict_theft_batch(df) -> DataFrame`
- `src/models/transformer_prediction/predict.py` → `predict_transformer_batch(df) -> DataFrame`

If the import or the call fails, the service falls back to the placeholder, so the demo never crashes.

## Input

The cleaned datasets, exactly as in `docs/data_dictionary.md`
(`data/processed/theft/theft_clean.csv`, `data/processed/transformer/transformer_clean.csv`).

## Output: theft (one row per `meter_id` + `month`)

| Column | Type | Meaning |
|---|---|---|
| `meter_id`, `month` | key | Same as input |
| `label` | `Normal` / `Suspicious` | Classification |
| `risk_score` | float 0-1 | Anomaly / risk score |
| `change_pct` | float | % change vs previous month |
| `recommendation` | text | Inspection advice |
| `source` | text | Model name, shown in the dashboard |

## Output: transformer (one row per `transformer_id` + `date`)

| Column | Type | Meaning |
|---|---|---|
| `transformer_id`, `date` | key | Same as input |
| `risk_level` | `Low` / `Medium` / `High` | Risk class |
| `failure_prob_7d` | float 0-1 | Estimated probability of failure within 7 days |
| `recommendation` | text | Maintenance advice |
| `source` | text | Model name |

Dashboard thresholds: High ≥ 30%, Medium ≥ 15% (placeholder values; the model owner may change them in `prediction_service.py`).

## Rules

1. Column names above do not change without telling the dashboard owner.
2. Predictions are inspection signals, never proof of theft or certain failure.
3. The transformer model must be evaluated on a chronological split, not a random one.
