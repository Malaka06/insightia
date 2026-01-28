from __future__ import annotations

from pathlib import Path
import streamlit as st


def inject_css(css_path: str | Path = "theme.css") -> None:
    """
    Injecte le thème global (CSS) dans Streamlit.
    À appeler une seule fois au tout début du rendu (avant header + pages).
    """
    p = Path(css_path)
    if not p.exists():
        # fallback: tente depuis le répertoire courant
        p = Path(__file__).parent / css_path

    css = p.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
