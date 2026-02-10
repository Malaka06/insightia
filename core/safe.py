from __future__ import annotations

from typing import Iterable, Optional, Sequence, Any, Dict
import pandas as pd


def best_col(candidates: Sequence[str], cols: Iterable[str]) -> Optional[str]:
    """
    Return the first matching column name from candidates, with tolerance to duplicates
    created by uniqueness helpers (e.g. 'date__2').
    """
    cols_list = [str(c) for c in cols]
    cols_set = set(cols_list)

    for c in candidates:
        if c in cols_set:
            return c

    # tolerate duplicated renaming patterns
    for c in candidates:
        prefix = f"{c}__"
        for existing in cols_list:
            if existing.startswith(prefix):
                return existing

    # light fuzzy: contains keyword
    lowered = {c.lower(): c for c in cols_list}
    for c in candidates:
        c_low = c.lower()
        for k_low, original in lowered.items():
            if c_low in k_low:
                return original

    return None


def make_columns_unique(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure unique column names to prevent Streamlit dataframe issues and KeyError surprises."""
    cols = [str(c) for c in df.columns]
    seen: Dict[str, int] = {}
    new_cols = []
    for c in cols:
        if c not in seen:
            seen[c] = 1
            new_cols.append(c)
        else:
            seen[c] += 1
            new_cols.append(f"{c}__{seen[c]}")
    out = df.copy()
    out.columns = new_cols
    return out


def to_dt(s: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(s, errors="coerce")
    except Exception:
        return pd.to_datetime(pd.Series([pd.NaT] * len(s)), errors="coerce")


def norm_text(s: pd.Series) -> pd.Series:
    return (
        s.fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def safe_mean_numeric(s: pd.Series) -> float | None:
    try:
        v = pd.to_numeric(s, errors="coerce")
        if v.notna().any():
            return float(v.mean())
    except Exception:
        return None
    return None
