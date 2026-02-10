from __future__ import annotations

from typing import Dict, Optional, Tuple
import pandas as pd
import streamlit as st
import altair as alt

from core.auto_nlp import (
    infer_theme_from_text,
    compute_words_top,
    compute_cooccurrence_top,
)
from core.metrics import (
    kpi_volume,
    kpi_neg_pct,
    kpi_avg_score,
    kpi_period,
)
from core.safe import best_col, to_dt
from ui.ui_components import info_box, safe_dataframe, missing_data, download_csv_button


# =========================================================
# Helpers
# =========================================================

def _header():
    st.markdown("# Analyse des retours clients")
    st.caption(
        "Comprendre ce que vos clients expriment réellement, identifier les sujets dominants "
        "et suivre l’évolution des irritants dans le temps."
    )

    info_box(
        "Comment lire cette analyse",
        "Cette page s’appuie uniquement sur les mots utilisés par les clients dans leurs messages. "
        "Les thèmes correspondent à des regroupements de messages similaires et non à des causes techniques. "
        "L’objectif est de rendre visible le signal client afin d’orienter les décisions métier.",
    )


def _get_base_df() -> Optional[pd.DataFrame]:
    for key in ["ana_nlp_df", "dataset_df"]:
        df = st.session_state.get(key)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df
    return None


def _insight_summary(df: pd.DataFrame):
    vol = kpi_volume(df)
    neg = kpi_neg_pct(df)
    avg = kpi_avg_score(df)
    dmin, dmax = kpi_period(df)

    parts = [f"**{vol:,} retours clients** analysés.".replace(",", " ")]
    if neg is not None:
        parts.append(f"**{neg}%** de retours négatifs.")
    if avg is not None:
        parts.append(f"Note moyenne : **{avg}**.")
    if dmin is not None and dmax is not None:
        parts.append(f"Période : **{dmin:%Y-%m-%d} → {dmax:%Y-%m-%d}**.")

    st.markdown(" ".join(parts))


# =========================================================
# SYNTHÈSE
# =========================================================

def _synthesis(df: pd.DataFrame, cols: Dict[str, str]):
    st.subheader("Synthèse du signal client")
    st.caption("Vue d’ensemble pour comprendre rapidement la situation.")

    _insight_summary(df)
    st.divider()

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Messages analysés", f"{kpi_volume(df):,}".replace(",", " "))
    neg = kpi_neg_pct(df)
    c2.metric("Part négative", "—" if neg is None else f"{neg}%")
    avg = kpi_avg_score(df)
    c3.metric("Note moyenne", "—" if avg is None else avg)
    dmin, dmax = kpi_period(df)
    c4.metric("Période", "—" if dmin is None else f"{dmin:%Y-%m-%d} → {dmax:%Y-%m-%d}")

    st.divider()

    # Thèmes dominants
    theme_col = cols.get("theme", "theme")
    if theme_col in df.columns:
        st.markdown("### Thèmes dominants")
        st.caption(
            "Les thèmes dominants indiquent les sujets les plus fréquemment évoqués par les clients. "
            "Ils montrent où se concentre le signal client."
        )

        top = (
            df[theme_col]
            .fillna("Autre")
            .astype(str)
            .value_counts()
            .head(8)
            .reset_index()
        )
        top.columns = ["Thème", "Volume"]

        chart = (
            alt.Chart(top)
            .mark_bar()
            .encode(
                y=alt.Y("Thème:N", sort="-x"),
                x=alt.X("Volume:Q"),
                tooltip=["Thème", "Volume"],
            )
            .properties(height=300)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        missing_data("Thèmes dominants", "Aucune colonne de thème détectée.")

    st.divider()

    # Nuage de mots (auto)
    st.markdown("### Mots les plus utilisés par les clients")
    st.caption(
        "Cette vue met en évidence le vocabulaire réellement utilisé par les clients. "
        "Les mots trop fréquents et peu informatifs sont automatiquement filtrés."
    )

    words = compute_words_top(df)
    if not words.empty:
        st.bar_chart(words.set_index("word").head(15))
    else:
        missing_data("Nuage de mots", "Impossible de calculer les mots clés.")


# =========================================================
# EXPLORER
# =========================================================

def _explorer(df: pd.DataFrame, cols: Dict[str, str]):
    st.subheader("Explorer les retours clients")
    st.caption(
        "Passez du signal global aux messages concrets pour comprendre pourquoi "
        "certains thèmes émergent."
    )

    theme_col = cols.get("theme", "theme")
    if theme_col not in df.columns:
        missing_data("Exploration", "Aucune colonne de thème disponible.")
        safe_dataframe(df.head(50))
        return

    theme = st.selectbox(
        "Sélectionnez un thème",
        sorted(df[theme_col].dropna().unique().tolist()),
    )

    sub = df[df[theme_col] == theme].copy()

    st.markdown("#### Lecture métier")
    st.caption(
        "Les messages ci-dessous sont rattachés à ce thème en fonction des mots détectés. "
        "Les mots déclencheurs permettent de comprendre pourquoi ce message a été regroupé ici."
    )

    view_cols = []
    for c in ["texte", "matched_keywords", "theme_score"]:
        if c in sub.columns:
            view_cols.append(c)

    safe_dataframe(sub[view_cols], height=420)
    download_csv_button(sub[view_cols], f"verbatims_{theme}.csv")

    st.divider()

    st.markdown("#### Relations entre les mots")
    st.caption(
        "Cette table montre les mots qui apparaissent fréquemment ensemble dans les messages, "
        "ce qui aide à mieux comprendre les associations récurrentes."
    )

    co = compute_cooccurrence_top(sub)
    if not co.empty:
        safe_dataframe(co, height=300)
    else:
        missing_data("Relations de mots", "Pas assez de données pour calculer les cooccurrences.")


# =========================================================
# CONTEXTE
# =========================================================

def _context():
    st.subheader("Contextes d’apparition des retours")
    st.caption(
        "Cette vue permet d’identifier dans quelles situations les retours clients apparaissent le plus souvent."
    )

    info_box(
        "Message important",
        "Les contextes observés décrivent des conditions d’apparition, "
        "pas des causes techniques directes.",
    )

    st.info("Bloc contextuel à enrichir selon les données disponibles (canal, parcours, situation…).")


# =========================================================
# TENDANCES
# =========================================================

def _trends(df: pd.DataFrame, cols: Dict[str, str]):
    st.subheader("Évolution du signal dans le temps")
    st.caption(
        "Suivez l’évolution des thèmes et du volume de retours pour détecter "
        "des améliorations ou des dégradations progressives."
    )

    date_col = cols.get("date")
    theme_col = cols.get("theme", "theme")

    if not date_col or date_col not in df.columns:
        missing_data("Tendances", "Aucune colonne de date détectée.")
        return

    tmp = df.copy()
    tmp["_dt"] = to_dt(tmp[date_col])
    tmp = tmp[tmp["_dt"].notna()]
    tmp["mois"] = tmp["_dt"].dt.to_period("M").astype(str)

    agg = (
        tmp.groupby(["mois", theme_col])
        .size()
        .reset_index(name="Volume")
    )

    chart = (
        alt.Chart(agg)
        .mark_line(point=True)
        .encode(
            x="mois:N",
            y="Volume:Q",
            color=f"{theme_col}:N",
            tooltip=["mois", "Volume", theme_col],
        )
        .properties(height=360)
    )

    st.altair_chart(chart, use_container_width=True)


# =========================================================
# MAIN
# =========================================================

def render():
    _header()

    base_df = _get_base_df()
    if base_df is None:
        st.info("Aucune donnée disponible. Importez un fichier ou lancez une démo.")
        return

    # Auto NLP (themes + explicabilité)
    df = infer_theme_from_text(base_df)

    cols = {
        "theme": "theme",
        "date": best_col(["date", "created_at", "timestamp"], df.columns),
    }

    tabs = st.tabs(["Synthèse", "Explorer", "Contexte", "Tendances"])

    with tabs[0]:
        _synthesis(df, cols)

    with tabs[1]:
        _explorer(df, cols)

    with tabs[2]:
        _context()

    with tabs[3]:
        _trends(df, cols)

    st.caption(
        "Cette analyse vise à faciliter la compréhension du signal client. "
        "Elle ne remplace ni l’expertise métier ni l’analyse terrain."
    )
