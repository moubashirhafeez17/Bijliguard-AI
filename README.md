# BijliGuard

AI-based electricity theft detection and transformer fault prediction. Exhibition prototype for Karachi.

> **Prototype notice.** All data here is simulated. A "Suspicious" meter is a signal for inspection, not proof of theft.
> Transformer risk is an estimate. This is not an operational K-Electric system.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python scripts/run_pipeline.py   # generate, clean, validate, save data + figures
streamlit run app.py             # open the dashboard
```

If you skip the pipeline step, the dashboard runs it automatically on first start.

## What is included (analytical part)

**Data pipeline**
- `scripts/generate_synthetic_data.py` makes dirty, simulated Karachi theft and transformer data.
- `src/data/clean_data.py` fixes duplicates, spellings, missing values and sensor glitches.
- `src/data/validate_data.py` checks the result. `reports/data_quality_report.json` records every change.
- `docs/data_dictionary.md` documents each column and marks what is simulated.
- `reports/figures/` holds 9 exploratory charts for the report.

**Dashboard (Streamlit)**
- Overview: summary cards, area risk, alerts.
- Theft Detection: meter search, history chart, flagged list, "try a reading" form.
- Transformer Monitoring: readings, 7-day risk, what-if sliders.
- Karachi Area Map: area-wise risk circles. Street map when online, built-in offline bubble map otherwise.

## Connecting the AI models

The dashboard reads predictions only from `src/services/prediction_service.py`.
Today it returns placeholder rule-based scores (labelled in the sidebar). To plug in the trained models,
see `docs/integration_contract.md`.

## Offline exhibition checklist

1. Install everything beforehand: `pip install -r requirements.txt`.
2. Run `python scripts/run_pipeline.py` once so the data files exist.
3. The Karachi Area Map page switches to its built-in **offline map** automatically when there is no internet (the street map needs a connection).
4. Start with `streamlit run app.py` and test with Wi-Fi off.

## Tests

```bash
python -m pytest -q tests
```
