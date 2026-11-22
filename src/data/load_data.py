"""Load raw or processed data.

Raw loaders look for PUBLIC datasets first (data/raw/...). If none are present
they fall back to the clearly-labelled SYNTHETIC files, and report which
source was used so the dashboard can show it honestly.
"""
from pathlib import Path

import pandas as pd

from config import settings as S


def _first_csv(folder: Path):
    files = sorted(folder.glob("*.csv"))
    return files[0] if files else None


def load_theft_raw():
    """Return (dataframe, source_label)."""
    public = _first_csv(S.RAW_THEFT_DIR)
    if public is not None:
        return pd.read_csv(public), f"public: {public.name}"
    return pd.read_csv(S.SYNTH_THEFT_RAW), "synthetic"


def load_transformer_raw():
    public = _first_csv(S.RAW_TRANSFORMER_DIR)
    if public is not None:
        return pd.read_csv(public), f"public: {public.name}"
    return pd.read_csv(S.SYNTH_TRANSFORMER_RAW), "synthetic"


def load_areas():
    path = S.AREAS_PROCESSED if S.AREAS_PROCESSED.exists() else S.SYNTH_AREAS
    return pd.read_csv(path)


def load_theft_processed():
    return pd.read_csv(S.THEFT_PROCESSED, parse_dates=["month"])


def load_transformer_processed():
    return pd.read_csv(S.TRANSFORMER_PROCESSED, parse_dates=["date"])
