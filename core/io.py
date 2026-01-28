# insightia/core/io.py
from __future__ import annotations
import pandas as pd


def read_csv_robust(uploaded_file) -> pd.DataFrame:
    try:
        return pd.read_csv(uploaded_file)
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, encoding="latin1")
    except Exception:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, sep=";")


def detect_text_column(df: pd.DataFrame) -> str:
    preferred = [
        "commentaire", "commentaires", "verbatim", "avis", "feedback",
        "texte", "text", "message", "description", "review"
    ]
    lower_map = {c.lower(): c for c in df.columns}
    for key in preferred:
        if key in lower_map:
            return lower_map[key]

    obj_cols = [c for c in df.columns if df[c].dtype == "object"]
    if not obj_cols:
        return str(df.columns[0])

    scores = []
    for c in obj_cols:
        non_null = df[c].notna().sum()
        avg_len = df[c].dropna().astype(str).str.len().mean() if non_null else 0
        scores.append((non_null, avg_len, c))

    scores.sort(reverse=True)
    return scores[0][2]


def ensure_text(df: pd.DataFrame, text_col: str) -> pd.DataFrame:
    out = df.copy()
    out[text_col] = out[text_col].fillna("").astype(str).str.strip()
    return out


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")
