from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List, Tuple

import pandas as pd
import streamlit as st
import altair as alt

from core.scoring import theme_table, backlog_from_theme_table, ImpactWeights


# ============================================================
# Persistence (for new tabs / new sessions)
# ============================================================

PERSIST_FILE = Path("data") / "last_nlp.parquet"
PERSIST_BACKLOG_FILE = Path("data") / "last_backlog.parquet"


# ============================================================
# UI PREMIUM (même langage visuel que Analysis)
# ============================================================

def _inject_premium_css():
    st.markdown(
        """
        <style>
          :root{
            --bg: #070b14;
            --card: rgba(15,23,42,.72);
            --muted: #94a3b8;
            --text: #e2e8f0;
            --border: rgba(148,163,184,.18);
            --shadow: 0 12px 28px rgba(2,6,23,.25);

            --primary: #2563eb;
            --primary2: rgba(37,99,235,.14);
            --success: #16a34a;
            --success2: rgba(22,163,74,.14);
            --warn: #f59e0b;
            --warn2: rgba(245,158,11,.14);
            --danger: #ef4444;
            --danger2: rgba(239,68,68,.14);
          }

          .stApp{
            background:
              radial-gradient(1200px 600px at 10% 0%, rgba(37,99,235,.18), transparent 45%),
              radial-gradient(900px 500px at 90% 10%, rgba(239,68,68,.14), transparent 55%),
              var(--bg);
            color: var(--text);
          }

          h1,h2,h3{ letter-spacing:-0.02em; }

          .ix-card{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 16px 16px 14px 16px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(10px);
          }
          .ix-row{ display:flex; gap:12px; flex-wrap:wrap; }
          .ix-help{
            margin-top: 8px;
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.35rem;
          }
          .ix-badge{
            display:inline-flex;
            align-items:center;
            gap:6px;
            padding: 6px 10px;
            border-radius: 999px;
            border: 1px solid var(--border);
            font-size: 0.86rem;
            color: var(--text);
            background: rgba(2,6,23,.35);
          }
          .ix-badge-primary{ background: var(--primary2); border-color: rgba(37,99,235,.35); }
          .ix-badge-success{ background: var(--success2); border-color: rgba(22,163,74,.35); }
          .ix-badge-warn{ background: var(--warn2); border-color: rgba(245,158,11,.35); }
          .ix-badge-danger{ background: var(--danger2); border-color: rgba(239,68,68,.35); }

          .ix-title{ font-size: 1.25rem; font-weight: 750; margin: 6px 0 0 0; }
          .ix-subtitle{ color: var(--muted); margin: 6px 0 0 0; font-size: 0.95rem; }

          .stTextInput input,
          .stSelectbox div[data-baseweb="select"] > div,
          .stMultiSelect div[data-baseweb="select"] > div{
            border-radius: 14px !important;
          }

          [data-testid="stDataFrame"]{
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid var(--border);
          }

          .stButton > button{
            border-radius: 14px !important;
            padding: 10px 14px !important;
            font-weight: 650 !important;
          }

          .stCaption{ color: var(--muted) !important; }
          hr{ border-color: var(--border) !important; }

          .ix-mini{
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 12px 12px 10px 12px;
            background: rgba(2,6,23,.25);
          }
          .ix-mini h4{ margin: 0 0 6px 0; font-size: 1.02rem; }
          .ix-mini p{ margin: 0; color: var(--muted); line-height: 1.35rem; font-size: 0.92rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _section_intro(title: str, subtitle: str, badges: Optional[List[Tuple[str, str]]] = None):
    badges = badges or []
    badges_html = " ".join([f"<span class='ix-badge {cls}'>{txt}</span>" for txt, cls in badges])
    st.markdown(
        f"""
        <div class="ix-card">
          <div class="ix-row" style="justify-content:space-between; align-items:center;">
            <div>
              <div class="ix-title">{title}</div>
              <div class="ix-subtitle">{subtitle}</div>
            </div>
            <div style="display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end;">
              {badges_html}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _help(text: str):
    st.markdown(f"<div class='ix-help'>{text}</div>", unsafe_allow_html=True)


# ============================================================
# OUTILS SIMPLES (sans jargon)
# ============================================================

def _priority_rank(p: str) -> int:
    s = str(p or "").strip().upper()
    m = re.match(r"^P(\d+)$", s)
    return int(m.group(1)) if m else 9


def _severity_rank(sv: str) -> int:
    s = str(sv or "").strip().upper()
    m = re.match(r"^S(\d+)$", s)
    return int(m.group(1)) if m else 9


def _contains_filter(df: pd.DataFrame, query: str, cols: List[str]) -> pd.DataFrame:
    q = (query or "").strip().lower()
    if not q:
        return df
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return df
    mask = pd.Series(False, index=df.index)
    for c in cols:
        mask |= df[c].fillna("").astype(str).str.lower().str.contains(q, na=False)
    return df[mask]


def _pick_examples(nlp_df: pd.DataFrame, theme_value: str, k: int = 8) -> pd.DataFrame:
    """Exemples représentatifs : bloquants > négatifs > confiance."""
    df = nlp_df.copy()
    if "theme" in df.columns:
        df = df[df["theme"].astype(str) == str(theme_value)]
    if df.empty:
        return df

    df["_ord_block"] = df["blocking"].fillna(False).astype(int) if "blocking" in df.columns else 0
    df["_ord_neg"] = (df["sentiment"].fillna("") == "Négatif").astype(int) if "sentiment" in df.columns else 0
    df["_ord_conf"] = pd.to_numeric(df.get("confidence", 0.0), errors="coerce").fillna(0.0)
    df["_ord_lowc"] = df.get("low_confidence", False)
    df["_ord_lowc"] = df["_ord_lowc"].fillna(False).astype(int)

    df = df.sort_values(
        ["_ord_block", "_ord_neg", "_ord_conf", "_ord_lowc"],
        ascending=[False, False, False, True],
    )

    cols = [
        c for c in
        ["texte", "text_norm", "blocking", "blocking_reason", "sentiment", "confidence", "low_confidence"]
        if c in df.columns
    ]
    return df[cols].head(k).copy() if cols else df.head(k).copy()


# ============================================================
# MOTEUR BACKLOG (simple + robuste)
# ============================================================

def generate_backlog(topics_df: pd.DataFrame, p1_min_nb: int, weights: ImpactWeights) -> pd.DataFrame:
    """
    Backlog = regroupement par thématique avec score d'impact.
    - P0 = urgent
    - P1 = important (ou volumétrie forte)
    - P2 = à planifier
    """
    df = topics_df.copy()

    # Sécuriser colonnes minimales
    if "theme" not in df.columns:
        df["theme"] = "Inconnu"
    if "blocking" not in df.columns and "incident" in df.columns:
        df["blocking"] = df["incident"].fillna(False).astype(bool)
    if "sentiment" not in df.columns and "sentiment_pred" in df.columns:
        df["sentiment"] = df["sentiment_pred"].fillna("Neutre")
    if "sentiment" not in df.columns:
        df["sentiment"] = "Neutre"

    tt = theme_table(df)
    backlog = backlog_from_theme_table(tt, weights=weights).copy()

    # Règle “volume” : si pas P0, alors P1 si nb >= seuil sinon P2
    if {"priorite_finale", "nb"}.issubset(backlog.columns):
        mask_not_p0 = backlog["priorite_finale"].astype(str) != "P0"
        backlog.loc[mask_not_p0 & (backlog["nb"] >= int(p1_min_nb)), "priorite_finale"] = "P1"
        backlog.loc[mask_not_p0 & (backlog["nb"] < int(p1_min_nb)), "priorite_finale"] = "P2"

    # Tri “naturel”
    backlog["_prio_rank"] = backlog.get("priorite_finale", "P9").apply(_priority_rank)
    backlog["_sev_rank"] = backlog.get("severite_finale", "S9").apply(_severity_rank)

    if "impact_score" in backlog.columns:
        backlog = backlog.sort_values(["_prio_rank", "_sev_rank", "impact_score"], ascending=[True, True, False])
    else:
        backlog = backlog.sort_values(["_prio_rank", "_sev_rank"], ascending=[True, True])

    return backlog


# ============================================================
# GRAPHIQUES (UTILITAIRES, CLARIFIANTS)
# ============================================================

def _charts_overview(backlog: pd.DataFrame):
    # Répartition priorités
    if "priorite_finale" in backlog.columns:
        pr = backlog["priorite_finale"].fillna("—").astype(str).value_counts().reset_index()
        pr.columns = ["priorite_finale", "count"]
        pr["rank"] = pr["priorite_finale"].apply(_priority_rank)
        pr = pr.sort_values("rank")

        chart_prio = (
            alt.Chart(pr)
            .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
            .encode(
                x=alt.X("priorite_finale:N", sort=None, title="Priorité"),
                y=alt.Y("count:Q", title="Nombre d’actions"),
                tooltip=[alt.Tooltip("priorite_finale:N", title="Priorité"), alt.Tooltip("count:Q", title="Actions")],
            )
            .properties(height=260)
        )
        st.altair_chart(chart_prio, use_container_width=True)

    # Top impact
    if {"irritant", "impact_score"}.issubset(backlog.columns):
        top = backlog[["irritant", "impact_score"]].head(10).copy()
        chart_top = (
            alt.Chart(top)
            .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
            .encode(
                x=alt.X("irritant:N", sort="-y", title="Action (thématique)"),
                y=alt.Y("impact_score:Q", title="Impact estimé"),
                tooltip=[
                    alt.Tooltip("irritant:N", title="Action"),
                    alt.Tooltip("impact_score:Q", title="Impact", format=".2f"),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart(chart_top, use_container_width=True)

    # Répartition sévérités
    if "severite_finale" in backlog.columns:
        sv = backlog["severite_finale"].fillna("—").astype(str).value_counts().reset_index()
        sv.columns = ["severite_finale", "count"]
        sv["rank"] = sv["severite_finale"].apply(_severity_rank)
        sv = sv.sort_values("rank")

        chart_sv = (
            alt.Chart(sv)
            .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
            .encode(
                x=alt.X("severite_finale:N", sort=None, title="Sévérité"),
                y=alt.Y("count:Q", title="Nombre d’actions"),
                tooltip=[alt.Tooltip("severite_finale:N", title="Sévérité"), alt.Tooltip("count:Q", title="Actions")],
            )
            .properties(height=260)
        )
        st.altair_chart(chart_sv, use_container_width=True)

    # Courbe Pareto
    if "impact_score" in backlog.columns:
        pareto = backlog[["impact_score"]].copy()
        pareto["impact_score"] = pd.to_numeric(pareto["impact_score"], errors="coerce").fillna(0.0)
        pareto = pareto.sort_values("impact_score", ascending=False).reset_index(drop=True)
        pareto["rang"] = pareto.index + 1
        total = pareto["impact_score"].sum()
        pareto["impact_cumule"] = pareto["impact_score"].cumsum()
        pareto["part_cumulee"] = pareto["impact_cumule"] / (total if total > 0 else 1.0)

        chart_pareto = (
            alt.Chart(pareto)
            .mark_line(point=True)
            .encode(
                x=alt.X("rang:Q", title="Nombre d’actions (triées par impact décroissant)"),
                y=alt.Y("part_cumulee:Q", title="Part de l’impact total", axis=alt.Axis(format="%")),
                tooltip=[
                    alt.Tooltip("rang:Q", title="Action #"),
                    alt.Tooltip("part_cumulee:Q", title="Impact cumulé", format=".0%"),
                ],
            )
            .properties(height=280)
        )
        st.altair_chart(chart_pareto, use_container_width=True)


# ============================================================
# PAGE BACKLOG (PREMIUM)
# ============================================================

def render_backlog():
    _inject_premium_css()

    _section_intro(
        "Priorisez vos actions",
        "Transforme les retours utilisateurs en une liste d’actions claire : quoi faire en premier, et pourquoi.",
        badges=[("Décision", "ix-badge-primary"), ("Preuves", "ix-badge-success")],
    )
    _help(
        "Principe : une ligne = une action. "
        "Chaque action a une priorité (P0/P1/P2), une sévérité (S1/S2/S3) et des preuves (verbatims)."
    )

    # 1) Sources possibles : session_state, puis fallback parquet (nouvel onglet)
    topics = st.session_state.get("ana_nlp_df")
    if topics is None:
        topics = st.session_state.get("topics_df")

    if (topics is None or (hasattr(topics, "empty") and topics.empty)) and PERSIST_FILE.exists():
        try:
            topics = pd.read_parquet(PERSIST_FILE)
            st.session_state["ana_nlp_df"] = topics
        except Exception:
            topics = None

    if topics is None or (hasattr(topics, "empty") and topics.empty):
        st.warning("Je n’ai pas de résultats d’analyse disponibles.")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Aller à l’analyse", type="primary", use_container_width=True):
                st.query_params["page"] = "analysis"
                st.rerun()
        with c2:
            if st.button("Revenir à l’import", use_container_width=True):
                st.query_params["page"] = "start"
                st.rerun()
        st.caption("Astuce : si tu ouvres Priorisation dans un nouvel onglet, la session est différente. Le fallback parquet corrige ça.")
        return

    # ------------------------------------------------------------
    # 1) Paramètres (peu nombreux, très clairs)
    # ------------------------------------------------------------
    st.divider()
    _section_intro(
        "Réglages",
        "Deux réglages maximum : seuil “important” (P1) et équilibre blocage / volume / négatif.",
        badges=[("Simple", "ix-badge")],
    )
    _help(
        "Conseil : laisse les valeurs par défaut. "
        "Tu modifies uniquement si ton contexte l’exige (ex. très faible volume mais très critique)."
    )

    c1, c2, c3, c4 = st.columns([1.25, 1.0, 1.0, 1.0])
    with c1:
        p1_min_nb = st.number_input(
            "À partir de combien de retours une action devient “importante” (P1) ?",
            min_value=1,
            max_value=100000,
            value=100,
            step=10,
        )
    with c2:
        w_block = st.slider("Poids “bloquant”", 0.0, 1.0, 0.45, 0.05)
    with c3:
        w_vol = st.slider("Poids “volume”", 0.0, 1.0, 0.35, 0.05)
    with c4:
        w_neg = st.slider("Poids “insatisfaction”", 0.0, 1.0, 0.20, 0.05)

    s = max(1e-9, w_block + w_vol + w_neg)
    weights = ImpactWeights(w_volume=w_vol / s, w_blocking=w_block / s, w_neg=w_neg / s)

    # cache (pour que la page reste fluide)
    cache_key = (
        len(topics),
        int(p1_min_nb),
        round(weights.w_volume, 3),
        round(weights.w_blocking, 3),
        round(weights.w_neg, 3),
    )

    if st.session_state.get("backlog_cache_key") != cache_key:
        st.session_state["backlog_cache_key"] = cache_key
        st.session_state["backlog_df"] = generate_backlog(
            topics,
            p1_min_nb=int(p1_min_nb),
            weights=weights,
        )

        # Persistance du backlog (nouvel onglet / refresh)
        Path("data").mkdir(parents=True, exist_ok=True)
        st.session_state["backlog_df"].to_parquet(PERSIST_BACKLOG_FILE, index=False)

    backlog = st.session_state["backlog_df"].copy()

    # ------------------------------------------------------------
    # 2) Résumé
    # ------------------------------------------------------------
    st.divider()
    _section_intro(
        "Résumé",
        "Aperçu rapide avant de filtrer et choisir.",
        badges=[("Vue rapide", "ix-badge-primary")],
    )

    nb_actions = len(backlog)
    nb_p0 = int((backlog.get("priorite_finale") == "P0").sum()) if "priorite_finale" in backlog.columns else 0
    nb_p1 = int((backlog.get("priorite_finale") == "P1").sum()) if "priorite_finale" in backlog.columns else 0
    nb_p2 = int((backlog.get("priorite_finale") == "P2").sum()) if "priorite_finale" in backlog.columns else 0

    nb_block = int(topics["blocking"].fillna(False).astype(bool).sum()) if "blocking" in topics.columns else 0
    pct_block = int(round((nb_block / max(1, len(topics))) * 100))

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Actions à traiter", f"{nb_actions:,}".replace(",", " "))
    k2.metric("Retours “bloquants”", f"{nb_block:,}".replace(",", " "))
    k3.metric("Part bloquante", f"{pct_block} %")
    k4.metric("P0 / P1 / P2", f"{nb_p0} / {nb_p1} / {nb_p2}")

    # ------------------------------------------------------------
    # 3) Graphiques
    # ------------------------------------------------------------
    st.divider()
    _section_intro(
        "Vue d’ensemble",
        "Graphiques utiles pour décider plus vite.",
        badges=[("Clair", "ix-badge-success")],
    )
    _charts_overview(backlog)

    # ------------------------------------------------------------
    # 4) Filtres backlog
    # ------------------------------------------------------------
    st.divider()
    _section_intro(
        "Filtres",
        "Isole ce qui compte : urgences, thèmes, recherche.",
        badges=[("Shortlist", "ix-badge-warn")],
    )

    shortlist = st.toggle("Mode shortlist (afficher uniquement P0 + P1)", value=True, key="bl_shortlist")

    b = backlog.copy()
    if shortlist and "priorite_finale" in b.columns:
        b = b[b["priorite_finale"].astype(str).isin(["P0", "P1"])]

    f1, f2, f3, f4 = st.columns([1.5, 1.0, 1.0, 1.6])

    with f1:
        if "irritant" in b.columns:
            themes = sorted(b["irritant"].fillna("").astype(str).unique().tolist())
            themes = [t for t in themes if t.strip()]
            sel_t = st.multiselect("Thématiques", options=themes, default=themes, key="bl_f_themes")
            if sel_t:
                b = b[b["irritant"].astype(str).isin(sel_t)]

    with f2:
        if "priorite_finale" in b.columns:
            prios = sorted(b["priorite_finale"].fillna("").astype(str).unique().tolist(), key=_priority_rank)
            prios = [p for p in prios if p.strip()]
            sel_p = st.multiselect("Priorité", options=prios, default=prios, key="bl_f_prio")
            if sel_p:
                b = b[b["priorite_finale"].astype(str).isin(sel_p)]

    with f3:
        if "severite_finale" in b.columns:
            sevs = sorted(b["severite_finale"].fillna("").astype(str).unique().tolist(), key=_severity_rank)
            sevs = [s for s in sevs if s.strip()]
            sel_s = st.multiselect("Sévérité", options=sevs, default=sevs, key="bl_f_sev")
            if sel_s:
                b = b[b["severite_finale"].astype(str).isin(sel_s)]

    with f4:
        q = st.text_input("Recherche", value="", placeholder="ex. connexion, lenteur, bug…", key="bl_f_q")
        b = _contains_filter(
            b,
            q,
            cols=[c for c in ["irritant", "recommandation", "priorite_finale", "severite_finale"] if c in b.columns],
        )

    st.caption(f"Affichage : {len(b):,} action(s).".replace(",", " "))

    # ------------------------------------------------------------
    # 5) Tableau backlog
    # ------------------------------------------------------------
    st.markdown("### Backlog (filtré)")
    _help("Chaque ligne = une action. Lis la recommandation puis regarde les preuves en bas.")

    show_cols = [
        c for c in
        ["irritant", "nb", "nb_blocking", "part_blocking", "part_neg",
         "impact_score", "priorite_finale", "severite_finale", "recommandation"]
        if c in b.columns
    ]
    st.dataframe(b[show_cols], use_container_width=True, height=520)

    # Exports
    ex1, ex2 = st.columns([1, 1])
    with ex1:
        st.download_button(
            "Télécharger le backlog (CSV)",
            data=b[show_cols].to_csv(index=False).encode("utf-8"),
            file_name="insightia_backlog_filtre.csv",
            mime="text/csv",
            use_container_width=True,
            key="bl_dl_backlog",
        )
    with ex2:
        jira = pd.DataFrame()
        if "priorite_finale" in b.columns and "irritant" in b.columns:
            jira["Summary"] = b.apply(lambda r: f"[{r['priorite_finale']}] {r['irritant']}", axis=1)
        elif "irritant" in b.columns:
            jira["Summary"] = b["irritant"].astype(str)
        else:
            jira["Summary"] = ["Action"] * len(b)

        jira["Description"] = b["recommandation"].fillna("").astype(str) if "recommandation" in b.columns else ""
        st.download_button(
            "Export prêt pour Jira (CSV)",
            data=jira.to_csv(index=False).encode("utf-8"),
            file_name="insightia_jira_export.csv",
            mime="text/csv",
            use_container_width=True,
            key="bl_dl_jira",
        )

    # ------------------------------------------------------------
    # 6) Preuves (verbatims)
    # ------------------------------------------------------------
    st.divider()
    _section_intro(
        "Preuves (retours utilisateurs)",
        "Sélectionne une action et lis des exemples représentatifs.",
        badges=[("Justification", "ix-badge-success")],
    )
    _help("Objectif : expliquer chaque action en 1 phrase + 3–8 exemples concrets.")

    if b.empty or "irritant" not in b.columns:
        st.info("Sélectionne au moins une action dans les filtres pour voir les preuves.")
        return

    action = st.selectbox("Choisir une action", options=b["irritant"].astype(str).tolist(), index=0, key="bl_sel_action")
    k = st.slider("Nombre d’exemples", 3, 20, 8, 1, key="bl_k_examples")

    row = b[b["irritant"].astype(str) == str(action)].head(1)
    if not row.empty:
        r = row.iloc[0]
        d1, d2, d3, d4 = st.columns(4)
        if "nb" in row.columns:
            d1.metric("Volume", str(int(r["nb"])))
        if "nb_blocking" in row.columns:
            d2.metric("Bloquants", str(int(r["nb_blocking"])))
        if "priorite_finale" in row.columns:
            d3.metric("Priorité", str(r["priorite_finale"]))
        if "severite_finale" in row.columns:
            d4.metric("Sévérité", str(r["severite_finale"]))
        if "recommandation" in row.columns:
            st.markdown(
                f"<div class='ix-mini'><h4>Direction proposée</h4><p>{str(r['recommandation'])}</p></div>",
                unsafe_allow_html=True,
            )

    ex = _pick_examples(topics, action, k=int(k))
    st.markdown("#### Exemples")
    st.caption("On montre d’abord les retours les plus problématiques et les plus clairs.")
    st.dataframe(ex, use_container_width=True, height=420)

    st.download_button(
        "Télécharger ces exemples (CSV)",
        data=ex.to_csv(index=False).encode("utf-8"),
        file_name=f"insightia_preuves_{re.sub(r'[^a-zA-Z0-9_-]+','_',str(action))}.csv",
        mime="text/csv",
        use_container_width=True,
        key="bl_dl_examples",
    )


# ============================================================
#Entrée publique standard (OBLIGATOIRE)
# ============================================================

def render():
    """Page : Priorisation des actions (appelée via ?page=prioritization)."""
    render_backlog()
