from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional, List, Tuple
from collections import Counter

import pandas as pd
import streamlit as st
import altair as alt

from core.nlp import run_pipeline
from core.scoring import theme_table


# ============================================================
# Persistence (for new tabs / new sessions)
# ============================================================

PERSIST_DIR = Path("data")
PERSIST_FILE = PERSIST_DIR / "last_nlp.parquet"


# ============================================================
# Premium UI (CSS)
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
            --primary-2: rgba(37,99,235,.14);

            --success: #16a34a;
            --success-2: rgba(22,163,74,.14);

            --warning: #f59e0b;
            --warning-2: rgba(245,158,11,.14);

            --danger: #ef4444;
            --danger-2: rgba(239,68,68,.14);
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
          .ix-badge-primary{ background: var(--primary-2); border-color: rgba(37,99,235,.35); }
          .ix-badge-warn{ background: var(--warning-2); border-color: rgba(245,158,11,.35); }
          .ix-badge-danger{ background: var(--danger-2); border-color: rgba(239,68,68,.35); }
          .ix-badge-success{ background: var(--success-2); border-color: rgba(22,163,74,.35); }

          .ix-title{ font-size: 1.25rem; font-weight: 750; margin: 6px 0 0 0; }
          .ix-subtitle{ color: var(--muted); margin: 6px 0 0 0; font-size: 0.95rem; }

          .stTextInput input,
          .stSelectbox div[data-baseweb="select"] > div,
          .stMultiSelect div[data-baseweb="select"] > div,
          .stDateInput input{
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

          /* Optional: CTA layout helper */
          .analysis-cta{
            display:flex;
            gap:12px;
            margin-top: 8px;
          }
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
# Helpers
# ============================================================

def _guess_col(df: pd.DataFrame, keys: List[str]) -> Optional[str]:
    if df is None or df.empty:
        return None
    cols = [str(c) for c in df.columns]
    low = {c.lower(): c for c in cols}
    for k in keys:
        for cl, orig in low.items():
            if k in cl:
                return orig
    return None


def _safe_dt(s: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(s, errors="coerce")
    except Exception:
        return pd.to_datetime(pd.Series([None] * len(s)), errors="coerce")


def _hash_key(df: pd.DataFrame, text_col: str, source_col: str, date_col: str) -> str:
    head = df.head(200).to_csv(index=False).encode("utf-8", errors="ignore")
    h = hashlib.sha256(head).hexdigest()[:16]
    return f"{h}|{text_col}|{source_col}|{date_col}"


def _format_theme_label(theme: str) -> str:
    t = str(theme or "").strip()
    if t.lower() in ("autre", "inconnu"):
        return "Non classé (à analyser)"
    return t


def _top_tokens(series: pd.Series, topn: int = 20) -> List[Tuple[str, int]]:
    tokens = []
    for x in series.fillna("").astype(str):
        s = x.lower()
        s = re.sub(r"[^a-zàâçéèêëîïôùûüÿñæœ0-9\s-]", " ", s)
        parts = [p for p in s.split() if len(p) >= 4]
        tokens.extend(parts)
    return Counter(tokens).most_common(topn)


def _points_attention(tt: pd.DataFrame) -> List[str]:
    points: List[str] = []
    if tt is None or tt.empty:
        return points

    cols = set(tt.columns)

    if {"part_blocking", "nb", "theme"}.issubset(cols):
        high = tt[(tt["part_blocking"].fillna(0) >= 0.30) & (tt["nb"].fillna(0) >= 10)].head(3)
        for _, r in high.iterrows():
            points.append(
                f"⚠️ Taux de blocage élevé sur <b>{_format_theme_label(r['theme'])}</b> "
                f"({int(round(float(r['part_blocking']) * 100))}%, nb={int(r['nb'])})."
            )

    if {"part_low_conf", "nb", "theme"}.issubset(cols):
        lowc = tt[(tt["part_low_conf"].fillna(0) >= 0.50) & (tt["nb"].fillna(0) >= 10)].head(3)
        for _, r in lowc.iterrows():
            points.append(
                f"⚠️ Signal à valider sur <b>{_format_theme_label(r['theme'])}</b> "
                f"(incertitude {int(round(float(r['part_low_conf']) * 100))}%, nb={int(r['nb'])})."
            )

    if {"theme", "nb"}.issubset(cols):
        mask_nc = tt["theme"].astype(str).str.strip().str.lower().isin(["autre", "inconnu"])
        if mask_nc.any():
            nb_nc = int(tt.loc[mask_nc, "nb"].sum())
            if nb_nc > 0:
                points.append(f"⚠️ <b>{nb_nc} verbatims</b> sont <b>non classés</b> (Autre/Inconnu).")

    return points[:6]


# ============================================================
# Filtering utilities (strict, premium)
# ============================================================

def _contains_filter(df: pd.DataFrame, query: str, cols: List[str]) -> pd.DataFrame:
    q = (query or "").strip().lower()
    if not q:
        return df
    use_cols = [c for c in cols if c in df.columns]
    if not use_cols:
        return df

    mask = pd.Series(False, index=df.index)
    for c in use_cols:
        mask = mask | df[c].fillna("").astype(str).str.lower().str.contains(q, na=False)
    return df[mask]


def _df_explorer_table_filters(df: pd.DataFrame, *, key_prefix: str = "ana_tbl") -> pd.DataFrame:
    st.markdown("#### Filtres (tableau)")
    _help(
        "Ces filtres s’appliquent uniquement au tableau ci-dessous (données brutes). "
        "Ils ne relancent pas le NLP. Utilise-les pour vérifier un canal, une période ou un motif dans les commentaires."
    )

    work = df.copy()
    cols = list(work.columns)

    c1, c2, c3 = st.columns([1.3, 1.2, 1.5])
    with c1:
        col_filter = st.multiselect(
            "Colonnes à afficher",
            options=cols,
            default=cols[: min(len(cols), 8)],
            key=f"{key_prefix}_cols",
        )
    with c2:
        rows = st.slider("Lignes (max)", 50, 2000, 500, step=50, key=f"{key_prefix}_rows")
    with c3:
        q = st.text_input(
            "Recherche (tableau)",
            value="",
            placeholder="recherche multi-colonnes (ex. 'remboursement', 'erreur')",
            key=f"{key_prefix}_q",
        )

    use_cols = col_filter if col_filter else cols
    work = _contains_filter(work, q, cols=use_cols)
    work = work[use_cols] if use_cols else work
    work = work.head(int(rows))

    st.caption(f"Affichage : {len(work):,} ligne(s).".replace(",", " "))
    return work


def _post_nlp_filters_ui(nlp_df: pd.DataFrame, *, key_prefix: str = "ana_post") -> pd.DataFrame:
    st.markdown("#### Filtres (résultats NLP)")
    _help(
        "Ces filtres s’appliquent aux tableaux NLP ci-dessous (verbatims, non classé). "
        "Ils ne recalculent rien : ils servent à investiguer le résultat."
    )

    df = nlp_df.copy()

    has_theme = "theme" in df.columns
    has_sent = "sentiment" in df.columns
    has_block = "blocking" in df.columns
    has_lowc = "low_confidence" in df.columns

    c1, c2, c3 = st.columns([1.6, 1.1, 1.3])

    with c1:
        if has_theme:
            themes = sorted(df["theme"].fillna("").astype(str).unique().tolist())
            themes = [t for t in themes if t.strip()]
            label_map = {t: _format_theme_label(t) for t in themes}
            inv_map = {v: k for k, v in label_map.items()}

            selected_labels = st.multiselect(
                "Thématiques",
                options=[label_map[t] for t in themes],
                default=[label_map[t] for t in themes],
                key=f"{key_prefix}_themes",
            )
            selected_themes = [inv_map.get(x, x) for x in selected_labels] if selected_labels else []
        else:
            selected_themes = []

    with c2:
        mode = st.radio(
            "Type de signal",
            options=["Tous", "Incidents bloquants", "Négatifs", "Low confidence", "Non classé"],
            key=f"{key_prefix}_mode",
        )

    with c3:
        q = st.text_input(
            "Recherche dans verbatims",
            value="",
            placeholder="ex. remboursement, crash, impossible, erreur…",
            key=f"{key_prefix}_q",
        )

    with st.expander("Options avancées", expanded=False):
        a1, a2, a3 = st.columns([1.2, 1.2, 1.2])
        with a1:
            sentiments = sorted(df["sentiment"].fillna("").astype(str).unique().tolist()) if has_sent else []
            sentiments = [s for s in sentiments if s.strip()]
            sel_sent = st.multiselect(
                "Sentiments",
                options=sentiments,
                default=sentiments,
                key=f"{key_prefix}_sentiments",
            ) if sentiments else []
        with a2:
            limit = st.slider("Limiter l’affichage (lignes)", 50, 1000, 200, step=50, key=f"{key_prefix}_limit")
        with a3:
            sort_by = st.selectbox(
                "Trier par",
                options=["Bloquant → Négatif → Incertitude", "Incertitude (desc)", "Confiance (desc)"],
                key=f"{key_prefix}_sort",
            )

    if has_theme and selected_themes:
        df = df[df["theme"].astype(str).isin([str(t) for t in selected_themes])]

    if mode == "Incidents bloquants" and has_block:
        df = df[df["blocking"].fillna(False).astype(bool)]
    elif mode == "Négatifs" and has_sent:
        df = df[df["sentiment"].fillna("") == "Négatif"]
    elif mode == "Low confidence" and has_lowc:
        df = df[df["low_confidence"].fillna(False).astype(bool)]
    elif mode == "Non classé" and has_theme:
        df = df[df["theme"].astype(str).str.strip().str.lower().isin(["autre", "inconnu"])]

    if has_sent and "sel_sent" in locals() and sel_sent:
        df = df[df["sentiment"].fillna("").astype(str).isin(sel_sent)]

    text_cols = [c for c in ["texte", "text_norm", "_text"] if c in df.columns]
    df = _contains_filter(df, q, cols=text_cols)

    if "sort_by" in locals():
        if sort_by == "Incertitude (desc)" and "low_confidence" in df.columns:
            df["_ord"] = df["low_confidence"].fillna(False).astype(int)
            df = df.sort_values("_ord", ascending=False).drop(columns=["_ord"], errors="ignore")
        elif sort_by == "Confiance (desc)" and "confidence" in df.columns:
            df = df.sort_values("confidence", ascending=False, na_position="last")
        else:
            df["_ord_block"] = df["blocking"].fillna(False).astype(int) if has_block else 0
            df["_ord_neg"] = (df["sentiment"].fillna("") == "Négatif").astype(int) if has_sent else 0
            df["_ord_lowc"] = df["low_confidence"].fillna(False).astype(int) if has_lowc else 0
            df = df.sort_values(["_ord_block", "_ord_neg", "_ord_lowc"], ascending=False)
            df = df.drop(columns=["_ord_block", "_ord_neg", "_ord_lowc"], errors="ignore")

    if "limit" in locals():
        df = df.head(int(limit))

    st.caption(f"Affichage : {len(df):,} ligne(s) (après filtres).".replace(",", " "))
    return df


# ============================================================
# Core rendering
# ============================================================

def _header():
    _section_intro(
        "Analyse",
        "Explore tes données et investigue le signal : thèmes, verbatims, fiabilité et non classé.",
        badges=[("Exploration", "ix-badge-primary"), ("Qualité", "ix-badge")],
    )


def _apply_filters(df: pd.DataFrame, text_col: str, source_col: Optional[str], date_col: Optional[str]) -> pd.DataFrame:
    work = df.copy()

    work["_text"] = work[text_col].fillna("").astype(str) if text_col else ""
    work["_has_text"] = work["_text"].str.strip().ne("")

    if source_col:
        work["_source"] = work[source_col].fillna("Non renseigné").astype(str)
    else:
        work["_source"] = "Toutes sources"

    if date_col:
        work["_date"] = _safe_dt(work[date_col])
    else:
        work["_date"] = pd.NaT

    _section_intro(
        "Filtres",
        "Définis le périmètre à analyser (sources, période, recherche).",
        badges=[("Avant NLP", "ix-badge-primary")],
    )
    _help(
        "On commence par cadrer les données. "
        "Conseil : démarre petit (1 canal + période courte), puis élargis progressivement."
    )

    f1, f2, f3 = st.columns([1.4, 1.0, 1.6])

    with f1:
        sources = sorted(work["_source"].dropna().unique().tolist())
        selected_sources = st.multiselect("Sources", options=sources, default=sources, key="ana_filter_sources")

    with f2:
        non_empty = st.checkbox("Exclure les verbatims vides", value=True, key="ana_filter_non_empty")

    with f3:
        q = st.text_input(
            "Recherche texte",
            value="",
            placeholder="ex. export, crash, facture…",
            key="ana_filter_query",
        )

    filt = work.copy()
    if selected_sources:
        filt = filt[filt["_source"].isin(selected_sources)]
    if non_empty:
        filt = filt[filt["_has_text"]]
    if q.strip():
        qq = q.strip().lower()
        filt = filt[filt["_text"].str.lower().str.contains(qq, na=False)]

    if date_col and filt["_date"].notna().any():
        min_d = filt["_date"].min().date()
        max_d = filt["_date"].max().date()
        d1, d2 = st.date_input("Période", value=(min_d, max_d), key="ana_filter_range")
        filt = filt[(filt["_date"].dt.date >= d1) & (filt["_date"].dt.date <= d2)]
    else:
        st.caption("Période : aucune colonne date exploitable (ou toutes les dates sont vides).")

    return filt


def _charts_explorer(filt: pd.DataFrame, date_col_present: bool):
    _section_intro(
        "Visualisations",
        "Comprends rapidement la distribution : sources, volume dans le temps, longueur des verbatims.",
        badges=[("Avant NLP", "ix-badge-primary")],
    )
    _help(
        "Ces graphes aident à détecter des biais (source sur-représentée), des pics temporels, "
        "ou une qualité de texte insuffisante (verbatims trop courts)."
    )

    chart_source = (
        alt.Chart(filt)
        .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
        .encode(
            x=alt.X("_source:N", sort="-y", title="Source"),
            y=alt.Y("count():Q", title="Volume"),
            tooltip=[alt.Tooltip("_source:N", title="Source"), alt.Tooltip("count():Q", title="Volume")],
        )
        .properties(height=260)
    )
    st.altair_chart(chart_source, use_container_width=True)

    if date_col_present and filt["_date"].notna().any():
        ts = filt.dropna(subset=["_date"]).copy()
        ts["_day"] = ts["_date"].dt.date.astype(str)
        chart_ts = (
            alt.Chart(ts)
            .mark_line(point=True)
            .encode(
                x=alt.X("_day:N", title="Date", sort=None),
                y=alt.Y("count():Q", title="Volume"),
                tooltip=[alt.Tooltip("_day:N", title="Date"), alt.Tooltip("count():Q", title="Volume")],
            )
            .properties(height=240)
        )
        st.altair_chart(chart_ts, use_container_width=True)
    else:
        st.caption("Série temporelle : indisponible (pas de dates exploitables).")

    filt["_words"] = filt["_text"].fillna("").astype(str).str.split().str.len()
    chart_len = (
        alt.Chart(filt)
        .mark_bar()
        .encode(
            x=alt.X("_words:Q", bin=alt.Bin(maxbins=30), title="Longueur (mots)"),
            y=alt.Y("count():Q", title="Volume"),
            tooltip=[alt.Tooltip("count():Q", title="Volume")],
        )
        .properties(height=230)
    )
    st.altair_chart(chart_len, use_container_width=True)


def _table_explorer(filt: pd.DataFrame, original_cols: List[str]):
    _section_intro(
        "Tableau (données brutes)",
        "Inspecte les lignes avant NLP et applique des filtres dédiés au tableau.",
        badges=[("Table filtrable", "ix-badge")],
    )
    _help(
        "Ce tableau sert à vérifier la donnée brute (qualité, colonnes, exemples). "
        "Les filtres ci-dessous s’appliquent uniquement à ce tableau."
    )

    keep = [c for c in original_cols if not str(c).startswith("_")]
    show = filt.copy()
    show["source_detectee"] = show.get("_source", "—")
    if "_date" in show.columns:
        show["date_parsee"] = show["_date"]
    show["mots"] = show.get("_words", show.get("_text", "").astype(str).str.split().str.len())

    cols_out = keep + [c for c in ["source_detectee", "date_parsee", "mots"] if c in show.columns]
    base = show[cols_out].copy()

    filtered_table = _df_explorer_table_filters(base, key_prefix="ana_tbl_raw")
    st.dataframe(filtered_table, use_container_width=True, height=480)


def _run_nlp_on_filtered(filt: pd.DataFrame, text_col: str) -> pd.DataFrame:
    base = filt.copy()
    base["texte"] = base[text_col].fillna("").astype(str)

    if base["texte"].str.strip().eq("").all():
        return pd.DataFrame(
            columns=list(base.columns)
            + [
                "text_norm", "sentiment", "score_sentiment",
                "blocking", "blocking_reason",
                "journey", "journey_conf",
                "theme", "confidence", "methode_categorie", "low_confidence",
            ]
        )
    return run_pipeline(base)


def _tab_nlp_and_insights(filt: pd.DataFrame, text_col: str):
    _section_intro(
        "NLP & insights",
        "Lance l’analyse, puis investigue : thèmes, verbatims, fiabilité et non classé.",
        badges=[("Après NLP", "ix-badge-primary")],
    )
    _help(
        "Ici on transforme le texte en signal exploitable (sans décider des actions). "
        "La priorisation/backlog sera dans la page suivante."
    )

    run = st.button("Lancer l’analyse NLP", type="primary", use_container_width=True, key="ana_run_nlp")

    st.session_state.setdefault("ana_nlp_cache_key", None)
    st.session_state.setdefault("ana_nlp_df", None)

    key = _hash_key(filt, text_col, "_source", "_date")

    if run or (st.session_state["ana_nlp_df"] is not None and st.session_state["ana_nlp_cache_key"] == key):
        if run or st.session_state["ana_nlp_cache_key"] != key:
            with st.spinner("Analyse en cours…"):
                nlp_df = _run_nlp_on_filtered(filt, text_col=text_col)
            st.session_state["ana_nlp_df"] = nlp_df
            st.session_state["ana_nlp_cache_key"] = key

            # ---- Persist results for new tab / new session ----
            try:
                PERSIST_DIR.mkdir(exist_ok=True)
                nlp_df.to_parquet(PERSIST_FILE, index=False)
            except Exception:
                pass
        else:
            nlp_df = st.session_state["ana_nlp_df"]

        if nlp_df is None or nlp_df.empty:
            st.warning("Aucune ligne exploitable après filtrage (texte vide).")
            return

        total = len(nlp_df)
        has_block = "blocking" in nlp_df.columns
        has_sent = "sentiment" in nlp_df.columns
        has_theme = "theme" in nlp_df.columns
        has_lowc = "low_confidence" in nlp_df.columns

        nb_blocking = int(nlp_df["blocking"].fillna(False).astype(bool).sum()) if has_block else 0
        pct_blocking = int(round((nb_blocking / max(1, total)) * 100))

        nb_neg = int((nlp_df["sentiment"].fillna("") == "Négatif").sum()) if has_sent else 0
        pct_neg = int(round((nb_neg / max(1, total)) * 100))

        nb_themes = int(nlp_df["theme"].nunique()) if has_theme else 0

        if has_theme:
            mask_nc = nlp_df["theme"].astype(str).str.strip().str.lower().isin(["autre", "inconnu"])
            nb_non_classe = int(mask_nc.sum())
        else:
            nb_non_classe = 0
        pct_non_classe = int(round((nb_non_classe / max(1, total)) * 100))

        st.markdown("#### Indicateurs (résumé)")
        _help(
            "Ces indicateurs donnent la lecture rapide : volume analysé, intensité du blocage/négatif, "
            "et part de non classé (à clarifier)."
        )

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Verbatims analysés", f"{total:,}".replace(",", " "))
        c2.metric("Thématiques", str(nb_themes) if nb_themes else "—")
        c3.metric("Incidents bloquants (nb)", f"{nb_blocking:,}".replace(",", " "))
        c4.metric("Blocage (%)", f"{pct_blocking} %")
        c5.metric("Négatif (%)", f"{pct_neg} %")
        c6.metric("Non classé (%)", f"{pct_non_classe} %")

        st.divider()
        _section_intro(
            "Thématiques",
            "Vue agrégée par thème : volume, blocage, négatif, incertitude.",
            badges=[("Comparaison", "ix-badge"), ("À vérifier", "ix-badge-warn")],
        )
        _help(
            "Lis d’abord les “points d’attention”, puis vérifie dans les verbatims. "
            "Objectif : comprendre ce qui ressort, avant toute décision."
        )

        tt = theme_table(nlp_df)

        pts = _points_attention(tt)
        if pts:
            with st.expander("Points d’attention (automatiques)", expanded=True):
                st.markdown(
                    "<div class='ix-help'>Ces points ne sont pas des décisions : ce sont des signaux qui méritent une vérification.</div>",
                    unsafe_allow_html=True,
                )
                for p in pts:
                    st.markdown(f"- {p}", unsafe_allow_html=True)
        else:
            st.caption("Aucun point d’attention saillant sur ce périmètre.")

        st.dataframe(tt, use_container_width=True, height=320)

        chart_theme = (
            alt.Chart(tt)
            .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
            .encode(
                x=alt.X("theme:N", sort="-y", title="Thème"),
                y=alt.Y("nb:Q", title="Volume"),
                tooltip=[
                    alt.Tooltip("theme:N", title="Thème"),
                    alt.Tooltip("nb:Q", title="Volume"),
                    alt.Tooltip("part_blocking:Q", title="Part blocage", format=".0%"),
                    alt.Tooltip("part_neg:Q", title="Part négatif", format=".0%"),
                    alt.Tooltip("part_low_conf:Q", title="Incertitude", format=".0%"),
                ],
            )
            .properties(height=280)
        )
        st.altair_chart(chart_theme, use_container_width=True)

        st.divider()
        _section_intro(
            "Investigation (verbatims)",
            "Applique des filtres sur les résultats NLP et lis les verbatims correspondants.",
            badges=[("Filtres appliqués", "ix-badge-primary")],
        )

        filtered_nlp = _post_nlp_filters_ui(nlp_df, key_prefix="ana_post_all")

        st.markdown("#### Verbatims (résultats filtrés)")
        _help(
            "But : valider le signal par lecture. "
            "Commence par “Incidents bloquants”, puis regarde “Non classé” et “Low confidence” pour les zones ambiguës."
        )

        cols_show = []
        for c in [
            "texte", "theme", "blocking", "blocking_reason",
            "sentiment", "score_sentiment",
            "confidence", "low_confidence",
            "methode_categorie",
            "journey", "journey_conf",
        ]:
            if c in filtered_nlp.columns:
                cols_show.append(c)

        if "texte" not in cols_show:
            for c in ["_text", "text_norm"]:
                if c in filtered_nlp.columns:
                    cols_show.insert(0, c)
                    break

        st.dataframe(filtered_nlp[cols_show], use_container_width=True, height=520)

        st.divider()
        _section_intro(
            "Qualité & fiabilité du signal",
            "Mesure la part de classification incertaine et repère les thèmes à améliorer.",
            badges=[("Confiance", "ix-badge")],
        )
        _help(
            "Ici on mesure la robustesse : où le modèle est fiable, et où une validation humaine est nécessaire "
            "(taxonomie/règles à améliorer)."
        )

        nb_lowc = int(nlp_df["low_confidence"].fillna(False).astype(bool).sum()) if has_lowc else 0
        pct_lowc = int(round((nb_lowc / max(1, total)) * 100))

        if has_lowc and has_block and nb_blocking > 0:
            nb_lowc_block = int(
                (nlp_df["low_confidence"].fillna(False).astype(bool) & nlp_df["blocking"].fillna(False).astype(bool)).sum()
            )
            pct_lowc_block = int(round((nb_lowc_block / max(1, nb_blocking)) * 100))
        else:
            pct_lowc_block = 0

        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Low confidence (%)", f"{pct_lowc} %")
        q2.metric("Low conf sur bloquants (%)", f"{pct_lowc_block} %")
        q3.metric("Non classé (nb)", f"{nb_non_classe:,}".replace(",", " "))
        q4.metric("Non classé (%)", f"{pct_non_classe} %")

        if tt is not None and not tt.empty and "part_low_conf" in tt.columns:
            st.markdown("#### Thèmes les plus incertains")
            _help("Ce tableau aide à cibler les thèmes où améliorer les règles/taxonomie aura le plus d’impact.")
            uncertain = tt.sort_values(["part_low_conf", "nb"], ascending=False).head(10).copy()
            st.dataframe(uncertain, use_container_width=True, height=320)

        st.divider()
        _section_intro(
            "Non classé (Autre / Inconnu)",
            "Ce qui ne rentre pas proprement dans une thématique : opportunités pour enrichir la taxonomie.",
            badges=[("Discovery", "ix-badge-warn")],
        )
        _help(
            "Approche recommandée : lis des exemples → repère un pattern → crée/ajuste une thématique. "
            "Le non classé est normal au début : c’est ton moteur d’amélioration."
        )

        if has_theme:
            mask_nc2 = nlp_df["theme"].astype(str).str.strip().str.lower().isin(["autre", "inconnu"])
            nc = nlp_df[mask_nc2].copy()

            if nc.empty:
                st.success("Aucun verbatim non classé sur ce périmètre.")
            else:
                left, right = st.columns([1.0, 1.6])
                with left:
                    st.metric("Verbatims non classés", f"{len(nc):,}".replace(",", " "))
                    if "blocking" in nc.columns:
                        st.metric("Bloquants (non classés)", str(int(nc["blocking"].fillna(False).astype(bool).sum())))
                    if "low_confidence" in nc.columns:
                        st.metric("Low confidence (non classés)", str(int(nc["low_confidence"].fillna(False).astype(bool).sum())))

                with right:
                    col_tokens = "text_norm" if "text_norm" in nc.columns else ("texte" if "texte" in nc.columns else None)
                    if col_tokens:
                        top = _top_tokens(nc[col_tokens], topn=25)
                        if top:
                            st.markdown("#### Mots fréquents (non classé)")
                            _help("Aide à repérer rapidement les expressions récurrentes pour créer de nouvelles thématiques.")
                            st.dataframe(pd.DataFrame(top, columns=["mot", "count"]), use_container_width=True, height=320)
                        else:
                            st.info("Pas assez de contenu textuel pour extraire des mots fréquents.")
                    else:
                        st.info("Aucune colonne texte disponible pour analyser le non classé.")

                st.markdown("#### Exemples (non classé)")
                _help("Lis quelques verbatims représentatifs : c’est la base pour décider d’une nouvelle thématique.")
                cols_nc = [c for c in ["texte", "blocking", "blocking_reason", "sentiment", "confidence", "low_confidence"] if c in nc.columns]
                if cols_nc:
                    st.dataframe(nc[cols_nc].head(200), use_container_width=True, height=420)

        st.download_button(
            "Télécharger : données enrichies (NLP)",
            data=nlp_df.to_csv(index=False).encode("utf-8"),
            file_name="insightia_nlp_enrichi.csv",
            mime="text/csv",
            use_container_width=True,
            key="ana_dl_nlp",
        )

    else:
        st.info("Applique tes filtres, puis clique sur “Lancer l’analyse NLP”.")


# ============================================================
# Public entry
# ============================================================

def render_analysis():
    _inject_premium_css()
    _header()

    df = st.session_state.get("dataset_df")
    if df is None or (hasattr(df, "empty") and df.empty):
        st.warning("Aucune donnée chargée. Revenez à l’étape 1 pour charger une démo ou importer un fichier.")
        st.markdown("<a class='btn btn-primary' href='?page=start'>Revenir à l’étape 1</a>", unsafe_allow_html=True)
        return

    df = df.copy()

    _section_intro(
        "Paramètres",
        "Choisis les colonnes à utiliser (verbatims, source/canal, date).",
        badges=[("Robuste", "ix-badge")],
    )
    _help(
        "Assure-toi que la colonne “verbatims” contient bien du texte exploitable (commentaire, message, avis). "
        "La source/canal et la date sont optionnels mais utiles."
    )

    default_text = _guess_col(df, ["verbatim", "commentaire", "comment", "feedback", "texte", "avis", "message"])
    default_source = _guess_col(df, ["source", "canal", "channel", "origine", "type"])
    default_date = _guess_col(df, ["date", "created", "timestamp", "jour", "mois"])

    c1, c2, c3 = st.columns([1.4, 1, 1])
    with c1:
        text_col = st.selectbox(
            "Colonne de verbatims",
            options=[str(c) for c in df.columns],
            index=(list(df.columns).index(default_text) if default_text in df.columns else 0),
            key="ana_param_text",
        )
    with c2:
        source_col = st.selectbox(
            "Source / Canal (optionnel)",
            options=[None] + [str(c) for c in df.columns],
            index=(1 + list(df.columns).index(default_source)) if default_source in df.columns else 0,
            key="ana_param_source",
        )
    with c3:
        date_col = st.selectbox(
            "Date (optionnel)",
            options=[None] + [str(c) for c in df.columns],
            index=(1 + list(df.columns).index(default_date)) if default_date in df.columns else 0,
            key="ana_param_date",
        )

    # Filters (before NLP)
    filt = _apply_filters(df, text_col=text_col, source_col=source_col, date_col=date_col)

    st.divider()
    _section_intro(
        "Synthèse",
        "Résumé du périmètre filtré : volume, sources, qualité du texte.",
        badges=[("Avant NLP", "ix-badge-primary")],
    )
    _help(
        "Dernier check avant NLP : est-ce que le périmètre est cohérent ? "
        "Exemple : pas trop de vides, plusieurs sources, période correcte."
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Lignes filtrées", f"{len(filt):,}".replace(",", " "))
    k2.metric("Sources", str(filt["_source"].nunique()) if "_source" in filt.columns else "—")
    k3.metric("Colonnes", str(len(df.columns)))
    k4.metric("Verbatims vides (global)", str(int((df[text_col].fillna("").astype(str).str.strip() == "").sum())))

    st.divider()
    _charts_explorer(filt, date_col_present=bool(date_col))

    st.divider()
    _table_explorer(filt, original_cols=[str(c) for c in df.columns])

    st.divider()
    _tab_nlp_and_insights(filt, text_col=text_col)

    st.markdown(
        "<div class='ix-help' style='margin: 20px 0 8px 0;'>"
        "Astuce : si tu obtiens trop de “Non classé”, c’est un signal : ta taxonomie mérite d’être enrichie (c’est normal)."
        "</div>",
        unsafe_allow_html=True,
    )

    # ✅ INCASSABLE: navigation same-tab (keeps session_state)
    cta1, cta2 = st.columns([1, 1])
    with cta1:
        if st.button("Changer de données", use_container_width=True):
            st.query_params["page"] = "start"
            st.rerun()

    with cta2:
        if st.button("Priorisez vos actions", type="primary", use_container_width=True):
            st.query_params["page"] = "prioritization"
            st.rerun()


# ============================================================
# Entrée publique standard
# ============================================================

def render():
    render_analysis()
