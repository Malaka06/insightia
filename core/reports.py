# ui/pages/reports.py
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from core.reporting import build_executive_summary

PERSIST_NLP = Path("data") / "last_nlp.parquet"
PERSIST_BACKLOG = Path("data") / "last_backlog.parquet"


def _load_df_from_session_or_parquet(
    *,
    session_key: str,
    parquet_path: Path,
    save_back_to_session: bool = True,
) -> pd.DataFrame:
    """Charge un DataFrame depuis st.session_state, sinon depuis un parquet."""
    df = st.session_state.get(session_key)

    if isinstance(df, pd.DataFrame) and not df.empty:
        return df

    if parquet_path.exists():
        try:
            df = pd.read_parquet(parquet_path)
            if save_back_to_session and isinstance(df, pd.DataFrame):
                st.session_state[session_key] = df
            return df if isinstance(df, pd.DataFrame) else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    return pd.DataFrame()


def _rate_bool(series: pd.Series) -> float:
    """Robuste: gère bool, 0/1, NaN."""
    try:
        return pd.to_numeric(series, errors="coerce").fillna(0).mean()
    except Exception:
        return series.fillna(False).astype(bool).mean()


def render():
    st.title("📊 Reporting exécutif")
    st.caption("Consolidation automatique : Analyse NLP + Backlog priorisé + preuves.")

    # 1) Chargement robuste (session_state puis fallback disque)
    topics = _load_df_from_session_or_parquet(
        session_key="ana_nlp_df",
        parquet_path=PERSIST_NLP,
    )
    if topics.empty:
        # fallback secondaire si tu utilises parfois topics_df
        topics = st.session_state.get("topics_df") if isinstance(st.session_state.get("topics_df"), pd.DataFrame) else topics

    backlog = _load_df_from_session_or_parquet(
        session_key="backlog_df",
        parquet_path=PERSIST_BACKLOG,
    )

    # 2) Garde-fou : pas d’analyse → pas de report
    if topics is None or not isinstance(topics, pd.DataFrame) or topics.empty:
        st.warning("Aucune analyse disponible. Lance d’abord la page Analyse.")
        if st.button("➡️ Aller à l’analyse", type="primary", use_container_width=True):
            st.query_params["page"] = "analysis"
            st.rerun()
        return

    # 3) KPIs rapides
    st.divider()
    st.subheader("📌 Indicateurs clés")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Verbatims analysés", len(topics))

    if "sentiment" in topics.columns:
        neg_rate = (topics["sentiment"].astype(str) == "Négatif").mean()
        col2.metric("Négatif", f"{neg_rate:.0%}")
    else:
        col2.metric("Négatif", "—")

    if "blocking" in topics.columns:
        blk_rate = _rate_bool(topics["blocking"])
        col3.metric("Bloquant", f"{blk_rate:.0%}")
    else:
        col3.metric("Bloquant", "—")

    if not backlog.empty and "priorite_finale" in backlog.columns:
        p0 = int((backlog["priorite_finale"].astype(str) == "P0").sum())
        col4.metric("Actions critiques (P0)", p0)
    else:
        col4.metric("Actions critiques (P0)", "—")

    # 4) Synthèse exécutive
    st.divider()
    st.subheader("🧠 Synthèse exécutive")

    summary = build_executive_summary(topics=topics, backlog=backlog)
    st.dataframe(summary, use_container_width=True)

    st.download_button(
        "📥 Télécharger la synthèse (CSV)",
        data=summary.to_csv(index=False).encode("utf-8"),
        file_name="executive_summary.csv",
        use_container_width=True,
    )

    # 5) Backlog (plan d’action) — UX propre
    st.divider()
    st.subheader("🛠️ Plan d’action priorisé (Backlog)")

    if backlog.empty:
        st.warning("Analyse OK, mais backlog manquant. Lance la page Priorisation pour le générer.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("➡️ Aller à la priorisation", type="primary", use_container_width=True):
                st.query_params["page"] = "prioritization"
                st.rerun()
        with c2:
            st.caption("Astuce : un nouvel onglet = nouvelle session. Le fallback parquet aide si le fichier existe.")

        # Bouton visible même si backlog absent (désactivé)
        st.download_button(
            "📥 Télécharger le backlog (CSV)",
            data=b"",
            file_name="backlog_priorise.csv",
            disabled=True,
            use_container_width=True,
            help="Le backlog n’est pas encore généré. Lance la priorisation.",
        )
    else:
        shortlist = st.toggle("Shortlist : afficher uniquement P0 + P1", value=True)

        b = backlog.copy()

        if shortlist and "priorite_finale" in b.columns:
            b = b[b["priorite_finale"].astype(str).isin(["P0", "P1"])]

        if "impact_score" in b.columns:
            b["impact_score"] = pd.to_numeric(b["impact_score"], errors="coerce").fillna(0.0)
            b = b.sort_values("impact_score", ascending=False)

        cols = [c for c in ["irritant", "priorite_finale", "severite_finale", "impact_score", "nb", "recommandation"] if c in b.columns]
        st.dataframe(b[cols] if cols else b, use_container_width=True, height=440)

        st.download_button(
            "📥 Télécharger le backlog (CSV)",
            data=b.to_csv(index=False).encode("utf-8"),
            file_name="backlog_priorise.csv",
            use_container_width=True,
        )

        # 6) Preuves (verbatims)
        st.divider()
        st.subheader("🧾 Preuves (verbatims)")

        if "irritant" in b.columns and "theme" in topics.columns:
            options = b["irritant"].dropna().astype(str).unique().tolist()
            if options:
                irr = st.selectbox("Choisir un irritant", options=options)
                preuves = topics[topics["theme"].astype(str) == str(irr)]

                if preuves.empty:
                    st.info("Aucun verbatim associé à cet irritant (vérifie correspondance thème ↔ irritant).")
                else:
                    prefer = [c for c in ["texte", "blocking", "blocking_reason", "sentiment", "confidence"] if c in preuves.columns]
                    show = preuves[prefer] if prefer else preuves
                    st.dataframe(show.head(25), use_container_width=True, height=420)
