from __future__ import annotations

import io
from typing import Optional

import pandas as pd
import streamlit as st

from core.safe import make_columns_unique


def info_box(title: str, text: str) -> None:
    st.markdown(
        f"""
<div style="
  border: 1px solid rgba(148,163,184,.22);
  background: rgba(15,23,42,.35);
  padding: 14px 16px;
  border-radius: 16px;
  margin: 8px 0 14px 0;
">
  <div style="font-weight:800; margin-bottom:6px;">{title}</div>
  <div style="color: rgba(226,232,240,.78); line-height: 1.6;">{text}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def missing_data(label: str, hint: Optional[str] = None) -> None:
    msg = f"Donnée manquante : {label}."
    if hint:
        msg += f" {hint}"
    st.warning(msg)


def safe_dataframe(df: Optional[pd.DataFrame], *, height: int = 380) -> None:
    if df is None or (hasattr(df, "empty") and df.empty):
        st.info("Aucune donnée à afficher.")
        return
    st.dataframe(make_columns_unique(df), use_container_width=True, height=height)


def download_csv_button(df: Optional[pd.DataFrame], filename: str, label: str = "Télécharger (CSV)") -> None:
    if df is None or (hasattr(df, "empty") and df.empty):
        return
    st.download_button(
        label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )


def download_parquet_button(df: Optional[pd.DataFrame], filename: str, label: str = "Télécharger (Parquet)") -> None:
    if df is None or (hasattr(df, "empty") and df.empty):
        return
    buf = io.BytesIO()
    try:
        df.to_parquet(buf, index=False)
        st.download_button(
            label,
            data=buf.getvalue(),
            file_name=filename,
            mime="application/octet-stream",
            use_container_width=True,
        )
    except Exception:
        # parquet deps may be missing on some envs
        return
