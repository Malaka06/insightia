# ui/pages/reports.py
import streamlit as st
import pandas as pd

from core.reporting import build_executive_summary


def render():
    st.title("📊 Reporting exécutif")

    st.caption(
        "Synthèse automatique basée sur l’analyse des verbatims "
        "et la priorisation du backlog."
    )

    # Récupération des données depuis les autres pages
    topics = st.session_state.get("ana_nlp_df") or st.session_state.get("topics_df")
    backlog = st.session_state.get("backlog_df")

    if not isinstance(topics, pd.DataFrame) or topics.empty:
        st.warning(
            "Aucune analyse disponible. "
            "Veuillez d’abord lancer l’analyse NLP."
        )
        if st.button("Aller à l’analyse", type="primary"):
            st.query_params["page"] = "analysis"
            st.rerun()
        return

    # -----------------------------
    # KPIs rapides
    # -----------------------------
    col1, col2, col3 = st.columns(3)

    col1.metric("Verbatims analysés", len(topics))

    if "sentiment" in topics.columns:
        neg = (topics["sentiment"].astype(str) == "Négatif").mean()
        col2.metric("Négatif", f"{neg:.0%}")
    else:
        col2.metric("Négatif", "—")

    if "blocking" in topics.columns:
        try:
            blk = (
                pd.to_numeric(topics["blocking"], errors="coerce")
                .fillna(0)
                .mean()
            )
        except Exception:
            blk = topics["blocking"].fillna(False).astype(bool).mean()
        col3.metric("Bloquant", f"{blk:.0%}")
    else:
        col3.metric("Bloquant", "—")

    st.divider()

    # -----------------------------
    # Synthèse exécutive
    # -----------------------------
    st.subheader("🧠 Synthèse exécutive")

    summary = build_executive_summary(
        topics=topics,
        backlog=backlog,
    )

    st.dataframe(summary, use_container_width=True)

    st.download_button(
        "📥 Télécharger la synthèse (CSV)",
        data=summary.to_csv(index=False).encode("utf-8"),
        file_name="executive_summary.csv",
        use_container_width=True,
    )

    # -----------------------------
    # Backlog (si présent)
    # -----------------------------
    if isinstance(backlog, pd.DataFrame) and not backlog.empty:
        st.divider()
        st.subheader("🛠️ Plan d’action priorisé")

        cols = [
            c
            for c in [
                "irritant",
                "priorite_finale",
                "severite_finale",
                "impact_score",
                "recommandation",
            ]
            if c in backlog.columns
        ]

        st.dataframe(backlog[cols], use_container_width=True)

        st.download_button(
            "📥 Télécharger le backlog (CSV)",
            data=backlog.to_csv(index=False).encode("utf-8"),
            file_name="backlog.csv",
            use_container_width=True,
        )
