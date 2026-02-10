from __future__ import annotations

from typing import Optional, Tuple
import pandas as pd

from core.safe import best_col, to_dt, safe_mean_numeric


def kpi_period(df: pd.DataFrame, date_col: Optional[str] = None) -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    if df is None or df.empty:
        return None, None
    if date_col is None:
        date_col = best_col(["date", "created_at", "created", "timestamp", "time", "jour"], df.columns)
    if not date_col or date_col not in df.columns:
        return None, None
    dt = to_dt(df[date_col])
    if not dt.notna().any():
        return None, None
    return dt.min(), dt.max()


def kpi_volume(df: pd.DataFrame) -> int:
    return int(len(df)) if isinstance(df, pd.DataFrame) else 0


def kpi_neg_pct(df: pd.DataFrame, sentiment_col: Optional[str] = None) -> Optional[int]:
    if df is None or df.empty:
        return None
    if sentiment_col is None:
        sentiment_col = best_col(["sentiment", "tonalite", "polarity"], df.columns)
    if not sentiment_col or sentiment_col not in df.columns:
        return None
    s = df[sentiment_col].astype(str)
    return int(round((s == "Négatif").mean() * 100))


def kpi_avg_score(df: pd.DataFrame, score_col: Optional[str] = None) -> Optional[float]:
    if df is None or df.empty:
        return None
    if score_col is None:
        score_col = best_col(["csat", "nps", "score", "rating", "note", "satisfaction"], df.columns)
    if not score_col or score_col not in df.columns:
        return None
    m = safe_mean_numeric(df[score_col])
    if m is None:
        return None
    return round(m, 2)


def top_motifs(
    df: pd.DataFrame,
    motif_col: Optional[str] = None,
    sentiment_col: Optional[str] = None,
    n: int = 5,
) -> pd.DataFrame:
    """
    Returns a table:
    Motif | Volume | Part (%) | % négatif
    Works with either 'motif' or 'theme' as motif_col.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["Motif", "Volume", "Part (%)", "% négatif"])

    if motif_col is None:
        motif_col = best_col(["motif", "theme", "thematique", "topic"], df.columns)
    if not motif_col or motif_col not in df.columns:
        return pd.DataFrame(columns=["Motif", "Volume", "Part (%)", "% négatif"])

    if sentiment_col is None:
        sentiment_col = best_col(["sentiment", "tonalite", "polarity"], df.columns)

    total = max(1, len(df))
    vc = df[motif_col].fillna("Non renseigné").astype(str).value_counts().head(int(n))
    out = vc.rename("Volume").reset_index().rename(columns={"index": "Motif"})
    out["Part (%)"] = (out["Volume"] / total * 100).round(1)

    if sentiment_col and sentiment_col in df.columns:
        s = df[sentiment_col].astype(str)
        neg_mask = s == "Négatif"
        neg_rates = (
            df.assign(_neg=neg_mask)
              .groupby(motif_col)["_neg"]
              .mean()
              .mul(100)
              .round(0)
              .astype(int)
        )
        out["% négatif"] = out["Motif"].map(neg_rates).fillna(0).astype(int)
    else:
        out["% négatif"] = None

    return out
