"""One command for the whole analytical data pipeline.

    python scripts/run_pipeline.py            # generate (if needed) -> clean -> validate -> save -> figures
    python scripts/run_pipeline.py --regen    # force re-generating the synthetic data first
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import settings as S  # noqa: E402
from src.data import clean_data, load_data, validate_data  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regen", action="store_true", help="regenerate synthetic raw data")
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()

    needs_synth = not (S.SYNTH_THEFT_RAW.exists() and S.SYNTH_TRANSFORMER_RAW.exists())
    if args.regen or needs_synth:
        import generate_synthetic_data
        generate_synthetic_data.main()

    for d in (S.PROCESSED_THEFT_DIR, S.PROCESSED_TRANSFORMER_DIR, S.REPORTS_DIR, S.FIGURES_DIR):
        d.mkdir(parents=True, exist_ok=True)

    theft_raw, theft_src = load_data.load_theft_raw()
    trf_raw, trf_src = load_data.load_transformer_raw()

    theft, theft_rep = clean_data.clean_theft(theft_raw)
    trf, trf_rep = clean_data.clean_transformer(trf_raw)

    theft.to_csv(S.THEFT_PROCESSED, index=False)
    trf.to_csv(S.TRANSFORMER_PROCESSED, index=False)
    load_data.load_areas().to_csv(S.AREAS_PROCESSED, index=False)

    report = {
        "theft": {"source": theft_src, "cleaning": theft_rep, "validation": validate_data.validate_theft(theft)},
        "transformer": {"source": trf_src, "cleaning": trf_rep, "validation": validate_data.validate_transformer(trf)},
    }
    S.QUALITY_REPORT.write_text(json.dumps(report, indent=2, default=str))

    for name, sec in report.items():
        v = sec["validation"]
        print(f"[{name}] source={sec['source']}  rows {sec['cleaning']['rows_in']:,} -> {sec['cleaning']['rows_out']:,}  "
              f"validation={'PASS' if v['passed'] else 'FAIL'}")
        for k, val in sec["cleaning"].items():
            if k not in ("rows_in", "rows_out") and val:
                print(f"    {k}: {val}")
        for issue in v["issues"]:
            print(f"    ! {issue}")

    if not args.no_figures:
        from src.visualization import plot_charts
        paths = plot_charts.make_all_figures(theft, trf)
        print(f"figures saved: {len(paths)} -> {S.FIGURES_DIR.relative_to(S.ROOT)}")
    print(f"quality report -> {S.QUALITY_REPORT.relative_to(S.ROOT)}")


if __name__ == "__main__":
    main()
