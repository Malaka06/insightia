from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import pandas as pd
import streamlit as st

SUPPORTED_TABLE_EXTS = {".csv", ".parquet"}


def _read_csv_fallback(path: Path) -> Optional[pd.DataFrame]:
    try:
        try:
            return pd.read_csv(path, encoding="utf-8")
        except Exception:
            return pd.read_csv(path, encoding="latin-1")
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def load_csv_or_parquet(path: Union[str, Path]) -> Optional[pd.DataFrame]:
    """
    Read a CSV or Parquet file safely.
    Returns None if file doesn't exist or can't be read.
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None

    try:
        if p.suffix.lower() == ".csv":
            return _read_csv_fallback(p)
        if p.suffix.lower() == ".parquet":
            return pd.read_parquet(p)
    except Exception:
        return None
    return None


@st.cache_data(show_spinner=False)
def load_outputs(outputs_dir: Union[str, Path] = "outputs") -> Dict[str, pd.DataFrame]:
    """
    Load all CSV/Parquet files in outputs_dir into a dict {stem: df}.
    Missing dir -> {}.
    """
    base = Path(outputs_dir)
    out: Dict[str, pd.DataFrame] = {}

    if not base.exists() or not base.is_dir():
        return out

    for p in base.iterdir():
        if p.is_file() and p.suffix.lower() in SUPPORTED_TABLE_EXTS:
            df = load_csv_or_parquet(p)
            if isinstance(df, pd.DataFrame) and not df.empty:
                out[p.stem] = df

    return out


def file_exists(path: Union[str, Path]) -> bool:
    p = Path(path)
    return p.exists() and p.is_file()


def resolve_output_path(filename: str, outputs_dir: Union[str, Path] = "outputs") -> Path:
    return Path(outputs_dir) / filename


def load_optional_png(filename: str, outputs_dir: Union[str, Path] = "outputs") -> Optional[Path]:
    p = resolve_output_path(filename, outputs_dir=outputs_dir)
    return p if p.exists() and p.is_file() else None
