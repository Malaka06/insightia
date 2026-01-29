from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import streamlit as st
import altair as alt

from core.nlp import run_pipeline
from core.scoring import theme_table


# =========================================================
# PAGE ANALYSE — VERSION FINALE (CLIENT-FRIENDLY)
# - Aucun jargon data exposé (pas de "low confidence", "Autre/Inconnu", etc.)
# - Garde uniquement les blocs validés :
#   * Indicateurs (résumé)
#   * Thématiques (points d’attention + tableau + bar chart)
#   * Messages non rattachés (KPIs + exemples)
# - CTA vers priorisation + Export
# =========================================================

PERSIST_DIR = Path("data")
PERSIST_FILE = PERSIST_DIR / "last_nlp.parquet"


# ---------------------------------------------------------
# Premium CSS (lisible + aéré)
# ---------------------------------------------------------

def _inject_premium_css():
    st.markdown(
        """
<style>
  :root{
    --bg: #070b14;
    --card: rgba(15,23,42,.66);
    --muted: rgba(226,232,240,.72);
    --text: #e2e8f0;
    --border: rgba(148,163,184,.18);
    --shadow: 0 12px 28px rgba(2,6,23,.25);

    --primary: #2563eb;
    --primary-2: rgba(37,99,235,.14);

    --warn: #f59e0b;
    --warn-2: rgba(245,158,11,.14);

    --danger: #ef4444;
    --danger-2: rgba(239,68,68,.14);
  }

  .stApp{
    background:
      radial-gradient(1200px 600px at 10% 0%, rgba(37,99,235,.16), transparent 45%),
      radial-gradient(900px 500px at 90% 10%, rgba(239,68,68,.12), transparent 55%),
      var(--bg);
    color: var(--text);
  }

  h1,h2,h3{ letter-spacing:-0.02em; }
  .stCaption, .stMarkdown small { color: var(--muted) !important; }

  .ix-card{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 16px 16px 14px 16px;
    box-shadow: var(--shadow);
    backdrop-filter: blur(10px);
  }

  .ix-note{
    margin-top: 10px;
    margin-bottom: 14px;
    padding: 14px 16px;
    border-radius: 16px;
    border: 1px solid rgba(239,68,68,0.24);
    background: rgba(15,23,42,0.28);
  }
  .ix-note-title{
    font-weight: 750;
    margin-bottom: 6px;
  }
  .ix-note-text{
    font-size: 15px;
    line-height: 1.6;
    opacity: .94;
  }

  .ix-title{ font-size: 1.15rem; font-weight: 760; margin: 0; }
  .ix-subtitle{ color: var(--muted); margin: 6px 0 0 0; font-size: 0.95rem; line-height:1.45; }

  .ix-badges{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
  .ix-badge{
    display:inline-flex;
    align-items:center;
    gap:6px;
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid var(--border);
    font-size: 0.86rem;
    color: var(--text);
    background: rgba(2,6,23,.30);
  }
  .ix-badge-primary{ background: var(--primary-2); border-color: rgba(37,99,235,.32); }
  .ix-badge-warn{ background: var(--warn-2); border-color: rgba(245,158,11,.28); }
  .ix-badge-danger{ background: var(--danger-2); border-color: rgba(239,68,68,.28); }

  .ix-help{
    margin-top: 8px;
    margin-bottom: 6px;
    color: var(--muted);
    font-size: 0.94rem;
    line-height: 1.45rem;
  }

  .stButton > button{
    border-radius: 14px !important;
    padding: 10px 14px !important;
    font-weight: 650 !important;
  }

  [data-testid="stDataFrame"]{
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid var(--border);
  }

  hr{ border-color: var(--border) !important; }
</style>
        """,
        unsafe_allow_html=True,
    )


def _card_header(title: str, subtitle: str, badges: Optional[List[Tuple[str, str]]] = None):
    badges = badges or []
    badges_html = " ".join([f"<span class='ix-badge {cls}'>{txt}</span>" for txt, cls in badges])
    st.markdown(
        f"""
<div class="ix-card">
  <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
    <div style="min-width:260px;">
      <div class="ix-title">{title}</div>
      <div class="ix-subtitle">{subtitle}</div>
    </div>
    <div class="ix-badges">{badges_html}</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _help(text: str):
    st.markdown(f"<div class='ix-help'>{text}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Robust utilities
# ---------------------------------------------------------

def make_columns_unique(df: pd.DataFrame) -> pd.DataFrame:
    cols = [str(c) for c in df.columns]
    seen: Dict[str, int] = {}
    new_cols: List[str] = []
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


def st_dataframe_safe(df: pd.DataFrame, **kwargs):
    if df is None or (hasattr(df, "empty") and df.empty):
        st.info("Aucune donnée à afficher.")
        return
    st.dataframe(make_columns_unique(df), **kwargs)


def _best_col(candidates: Iterable[str], cols: Iterable[str]) -> Optional[str]:
    cols_set = {str(c) for c in cols}
    for c in candidates:
        if c in cols_set:
            return c
    for c in candidates:
        for existing in cols_set:
            if existing == c or existing.startswith(f"{c}__"):
                return existing
    return None


def _to_dt(s: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(s, errors="coerce")
    except Exception:
        return pd.to_datetime(pd.Series([pd.NaT] * len(s)), errors="coerce")


def _normalize_text(s: pd.Series) -> pd.Series:
    return (
        s.fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def _is_empty_text(s: pd.Series) -> pd.Series:
    return _normalize_text(s).eq("")


def _hash_key(df: pd.DataFrame, text_col: str, source_col: Optional[str], date_col: Optional[str]) -> str:
    head = df.head(250).to_csv(index=False).encode("utf-8", errors="ignore")
    h = hashlib.sha256(head).hexdigest()[:16]
    return f"{h}|{text_col}|{source_col or '—'}|{date_col or '—'}"


def _is_unlinked_theme(theme: str) -> bool:
    t = str(theme or "").strip().lower()
    return t in {"", "autre", "inconnu", "unknown", "other"}


def _public_theme_label(theme: str) -> str:
    # On ne montre jamais "Autre/Inconnu" au client : on affiche une version métier
    return "Messages non rattachés" if _is_unlinked_theme(theme) else str(theme).strip()


def _points_attention_public(tt: pd.DataFrame) -> List[str]:
    """
    Version client-friendly :
    - pas de 'low confidence'
    - pas de 'incertitude 63%'
    - pas de 'Autre/Inconnu'
    """
    points: List[str] = []
    if tt is None or tt.empty:
        return points

    cols = set(tt.columns)

    # 1) Blocage fort
    if {"part_blocking", "nb", "theme"}.issubset(cols):
        high = tt[(tt["part_blocking"].fillna(0) >= 0.30) & (tt["nb"].fillna(0) >= 10)].head(3)
        for _, r in high.iterrows():
            points.append(
                f"⚠️ Plusieurs retours indiquent une difficulté bloquante sur <b>{_public_theme_label(r['theme'])}</b> "
                f"(volume : {int(r['nb'])})."
            )

    # 2) Messages difficiles à interpréter (ex-low_conf)
    if {"part_low_conf", "nb", "theme"}.issubset(cols):
        hard = tt[(tt["part_low_conf"].fillna(0) >= 0.50) & (tt["nb"].fillna(0) >= 10)].head(3)
        for _, r in hard.iterrows():
            points.append(
                f"⚠️ Signal à relire sur <b>{_public_theme_label(r['theme'])}</b> : "
                f"une part importante des messages est difficile à interpréter (volume : {int(r['nb'])})."
            )

    # 3) Part non rattachée
    if {"theme", "nb"}.issubset(cols):
        mask_unlinked = tt["theme"].astype(str).apply(_is_unlinked_theme)
        if mask_unlinked.any():
            nb_unlinked = int(tt.loc[mask_unlinked, "nb"].sum())
            if nb_unlinked > 0:
                points.append(
                    f"⚠️ <b>{nb_unlinked} messages</b> ne sont pas rattachés à une thématique : "
                    "cela peut révéler un sujet émergent ou une zone à clarifier."
                )

    return points[:6]


def _tt_public_view(tt: pd.DataFrame) -> pd.DataFrame:
    """
    Renomme les colonnes techniques pour l'affichage client.
    On conserve les valeurs mais on met des libellés compréhensibles.
    """
    out = tt.copy()

    # thème public
    if "theme" in out.columns:
        out["Thématique"] = out["theme"].astype(str).apply(_public_theme_label)
    else:
        out["Thématique"] = "—"

    # colonnes possibles selon ton theme_table()
    colmap = {
        "nb": "Volume",
        "nb_blocking": "Situations bloquantes (nb)",
        "part_blocking": "Part de situations bloquantes (%)",
        "part_neg": "Part de retours négatifs (%)",
        "part_low_conf": "Messages difficiles à interpréter (%)",
    }

    # Crée des colonnes publiques si présentes
    for src, dst in colmap.items():
        if src in out.columns:
            if "part_" in src:
                out[dst] = (out[src].fillna(0) * 100).round(0).astype(int)
            else:
                out[dst] = out[src]

    # Colonnes finales à montrer (dans l'ordre)
    show = ["Thématique"]
    for dst in ["Volume", "Situations bloquantes (nb)", "Part de situations bloquantes (%)", "Part de retours négatifs (%)", "Messages difficiles à interpréter (%)"]:
        if dst in out.columns:
            show.append(dst)

    return out[show].sort_values("Volume", ascending=False) if "Volume" in out.columns else out[show]


def _nlp_examples_public(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tableau d'exemples client-friendly :
    - pas de 'low_confidence'
    - pas de 'confidence' brut
    """
    out = df.copy()

    # Colonnes sources possibles
    text_col = "texte" if "texte" in out.columns else ("text_norm" if "text_norm" in out.columns else None)
    if text_col and text_col != "texte":
        out["texte"] = out[text_col]

    # Colonnes publiques
    cols = []

    if "texte" in out.columns:
        out["Message"] = out["texte"].astype(str)
        cols.append("Message")

    if "sentiment" in out.columns:
        out["Tonalité"] = out["sentiment"].astype(str)
        cols.append("Tonalité")

    # "confidence" -> "Niveau de clarté" (0–100)
    if "confidence" in out.columns:
        out["Niveau de clarté"] = (out["confidence"].fillna(0).astype(float) * 100).round(0).astype(int)
        cols.append("Niveau de clarté")

    # low_confidence -> "À relire"
    if "low_confidence" in out.columns:
        out["À relire"] = out["low_confidence"].fillna(False).astype(bool).map({True: "Oui", False: "Non"})
        cols.append("À relire")

    # blocking -> "Bloquant"
    if "blocking" in out.columns:
        out["Bloquant"] = out["blocking"].fillna(False).astype(bool).map({True: "Oui", False: "Non"})
        cols.append("Bloquant")

    # blocking_reason (optionnel)
    if "blocking_reason" in out.columns:
        out["Pourquoi c’est bloquant"] = out["blocking_reason"].fillna("").astype(str)
        cols.append("Pourquoi c’est bloquant")

    if not cols:
        # fallback minimal
        return out.head(200)

    return out[cols].head(200)


# ---------------------------------------------------------
# Dataset access (robust)
# ---------------------------------------------------------

def _get_current_df() -> Tuple[Optional[pd.DataFrame], str]:
    preferred_keys = [
        "dataset_df",
        "df",
        "data_df",
        "uploaded_df",
        "uploaded_data",
        "raw_df",
        "import_df",
        "imported_df",
        "demo_df",
        "demo_data_df",
        "start_df",
    ]
    for k in preferred_keys:
        v = st.session_state.get(k)
        if isinstance(v, pd.DataFrame) and not v.empty:
            return v, f"session_state['{k}']"
    for k, v in st.session_state.items():
        if isinstance(v, pd.DataFrame) and not v.empty:
            return v, f"session_state['{k}']"
    return None, "—"


# ---------------------------------------------------------
# UI — Top header (H1 + CTA)
# ---------------------------------------------------------

def _h1_and_cta():
    left, right = st.columns([4.2, 1.2], vertical_alignment="top")
    with left:
        st.markdown("# Explorez les données clients")
        st.caption(
            "Analyse descriptive du signal client. "
            "Cette vue permet de comprendre ce qui ressort des retours clients avant toute priorisation ou décision."
        )
    with right:
        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
        if st.button("Passer à la priorisation →", use_container_width=True):
            st.query_params["page"] = "prioritization"
            st.rerun()


def _method_note():
    st.markdown(
        """
<div class="ix-note">
  <div class="ix-note-title">Note méthodologique</div>
  <div class="ix-note-text">
    Les résultats présentés ci-dessous dépendent strictement du périmètre sélectionné (sources, période, filtres).
    Toute modification met à jour instantanément les éléments affichés.
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# Core filters
# ---------------------------------------------------------

def _apply_filters(df: pd.DataFrame, text_col: str, source_col: Optional[str], date_col: Optional[str]) -> Tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    work = df.copy()
    work[text_col] = _normalize_text(work[text_col])

    _card_header(
        "Cadre des données analysées",
        "Les sources, la période et les filtres appliqués définissent le périmètre analysé.",
        badges=[("Périmètre", "ix-badge-primary")],
    )
    _help("Conseil : démarre petit (1 canal + période courte), puis élargis progressivement.")

    col1, col2, col3 = st.columns([2.2, 1.2, 1.6], vertical_alignment="bottom")

    with col1:
        st.markdown("**Sources**")
        if source_col:
            all_sources = sorted([s for s in work[source_col].dropna().astype(str).unique().tolist() if s.strip() != ""])
            selected_sources = st.multiselect(
                "Sources",
                options=all_sources,
                default=all_sources,
                label_visibility="collapsed",
                key="ana_sources",
            )
        else:
            selected_sources = []
            st.caption("Aucune colonne source détectée.")

    with col2:
        exclude_empty = st.checkbox("Exclure les messages vides", value=True, key="ana_excl_empty")

    with col3:
        q = st.text_input(
            "Recherche ciblée",
            value="",
            placeholder="ex. remboursement, crash, facture…",
            key="ana_q",
        )

    # Period filter
    start_dt = pd.NaT
    end_dt = pd.NaT
    if date_col:
        dt = _to_dt(work[date_col])
        work["_dt"] = dt
        min_dt = dt.dropna().min()
        max_dt = dt.dropna().max()
        if pd.notna(min_dt) and pd.notna(max_dt):
            d1, d2 = st.date_input(
                "Période",
                value=(min_dt.date(), max_dt.date()),
                min_value=min_dt.date(),
                max_value=max_dt.date(),
                key="ana_period",
            )
            start_dt = pd.Timestamp(d1)
            end_dt = pd.Timestamp(d2) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        else:
            st.caption("Période : colonne date non exploitable.")
    else:
        st.caption("Période : aucune colonne date détectée.")

    # Apply filters
    filt = work.copy()
    if source_col and selected_sources:
        filt = filt[filt[source_col].astype(str).isin(selected_sources)]
    if exclude_empty:
        filt = filt[~_is_empty_text(filt[text_col])]
    if q.strip():
        filt = filt[filt[text_col].str.contains(q.strip(), case=False, regex=False)]
    if date_col and "_dt" in filt.columns and pd.notna(start_dt) and pd.notna(end_dt):
        filt = filt[(filt["_dt"] >= start_dt) & (filt["_dt"] <= end_dt)]

    return filt, start_dt, end_dt


# ---------------------------------------------------------
# NLP run
# ---------------------------------------------------------

def _run_nlp(filt_df: pd.DataFrame, *, text_col: str) -> pd.DataFrame:
    base = filt_df.copy()
    base["texte"] = base[text_col].fillna("").astype(str)
    if base["texte"].str.strip().eq("").all():
        return pd.DataFrame(columns=list(base.columns) + ["theme", "blocking", "sentiment", "confidence", "low_confidence"])
    return run_pipeline(base)


# ---------------------------------------------------------
# Validated blocks (client wording)
# ---------------------------------------------------------

def _bloc_indicateurs(nlp_df: pd.DataFrame):
    st.markdown("#### Indicateurs (résumé)")
    st.markdown(
        "Ces indicateurs décrivent le signal observé.\n"
        "Ils servent à la compréhension, pas à la décision."
    )

    total = int(len(nlp_df))

    has_block = "blocking" in nlp_df.columns
    has_sent = "sentiment" in nlp_df.columns
    has_theme = "theme" in nlp_df.columns
    has_hard = "low_confidence" in nlp_df.columns

    nb_blocking = int(nlp_df["blocking"].fillna(False).astype(bool).sum()) if has_block else 0
    pct_blocking = int(round((nb_blocking / max(1, total)) * 100))

    nb_neg = int((nlp_df["sentiment"].fillna("") == "Négatif").sum()) if has_sent else 0
    pct_neg = int(round((nb_neg / max(1, total)) * 100))

    nb_themes = int(nlp_df["theme"].nunique()) if has_theme else 0

    mask_unlinked = (
        nlp_df["theme"].astype(str).apply(_is_unlinked_theme) if has_theme else pd.Series([False] * total)
    )
    nb_unlinked = int(mask_unlinked.sum())
    pct_unlinked = int(round((nb_unlinked / max(1, total)) * 100))

    nb_hard = int(nlp_df["low_confidence"].fillna(False).astype(bool).sum()) if has_hard else 0
    pct_hard = int(round((nb_hard / max(1, total)) * 100)) if has_hard else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Messages analysés", f"{total:,}".replace(",", " "))
    c2.metric("Thématiques", str(nb_themes) if nb_themes else "—")
    c3.metric("Situations bloquantes (nb)", f"{nb_blocking:,}".replace(",", " "))
    c4.metric("Part de messages bloquants (%)", f"{pct_blocking} %")
    c5.metric("Part de messages négatifs (%)", f"{pct_neg} %")
    c6.metric("Part de messages non rattachés (%)", f"{pct_unlinked} %")

    # Ligne d'info discrète (sans jargon)
    if has_hard:
        st.caption(f"Messages difficiles à interpréter : {pct_hard} % (sur le périmètre analysé).")


def _bloc_thematiques(nlp_df: pd.DataFrame):
    _card_header(
        "Thématiques",
        "Vue agrégée par thématique : volume, situations bloquantes, tonalité négative et lisibilité des messages.",
        badges=[("Comparaison", "ix-badge"), ("À relire", "ix-badge-warn")],
    )
    _help(
        "Lis d’abord les points d’attention, puis vérifie dans les verbatims. "
        "L’objectif est de comprendre ce qui ressort, avant toute décision."
    )

    tt = theme_table(nlp_df)
    if tt is None or tt.empty:
        st.info("Aucune thématique exploitable sur ce périmètre.")
        return

    pts = _points_attention_public(tt)
    if pts:
        with st.expander("Points d’attention (automatiques)", expanded=True):
            st.markdown(
                "<div class='ix-help'>Ces points ne sont pas des décisions : ce sont des signaux qui méritent une vérification.</div>",
                unsafe_allow_html=True,
            )
            for p in pts:
                st.markdown(f"- {p}", unsafe_allow_html=True)

    tt_pub = _tt_public_view(tt)
    st_dataframe_safe(tt_pub, use_container_width=True, height=320)

    # Bar chart (volume)
    chart = (
        alt.Chart(tt_pub)
        .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
        .encode(
            x=alt.X("Thématique:N", sort="-y", title="Thématique"),
            y=alt.Y("Volume:Q", title="Volume"),
            tooltip=[
                alt.Tooltip("Thématique:N", title="Thématique"),
                alt.Tooltip("Volume:Q", title="Volume"),
            ],
        )
        .properties(height=280)
    )
    st.altair_chart(chart, use_container_width=True)


def _bloc_messages_non_rattaches(nlp_df: pd.DataFrame):
    _card_header(
        "Messages non rattachés à une thématique",
        "Certains retours ne correspondent pas encore clairement à une thématique existante.",
        badges=[("À clarifier", "ix-badge-warn")],
    )
    _help(
        "Ces messages ne correspondent pas encore clairement à une thématique existante. "
        "Ils permettent souvent d’identifier de nouveaux sujets ou des points de friction émergents."
    )

    if "theme" not in nlp_df.columns:
        st.info("Cette vue nécessite une colonne de thématique.")
        return

    mask_unlinked = nlp_df["theme"].astype(str).apply(_is_unlinked_theme)
    nr = nlp_df[mask_unlinked].copy()

    if nr.empty:
        st.success("Aucun message non rattaché sur ce périmètre.")
        return

    k1, k2, k3 = st.columns(3)
    k1.metric("Messages non rattachés", f"{len(nr):,}".replace(",", " "))
    if "blocking" in nr.columns:
        k2.metric("Situations bloquantes (non rattachés)", str(int(nr["blocking"].fillna(False).astype(bool).sum())))
    else:
        k2.metric("Situations bloquantes (non rattachés)", "—")

    if "low_confidence" in nr.columns:
        k3.metric("Messages difficiles à interpréter (non rattachés)", str(int(nr["low_confidence"].fillna(False).astype(bool).sum())))
    else:
        k3.metric("Messages difficiles à interpréter (non rattachés)", "—")

    st.markdown("#### Exemples (messages non rattachés)")
    _help("Lis quelques messages représentatifs : c’est la base pour clarifier de nouveaux sujets ou ajuster les règles.")

    st_dataframe_safe(_nlp_examples_public(nr), use_container_width=True, height=420)


def _exports(nlp_df: pd.DataFrame):
    st.markdown("#### Export")
    st.caption("Télécharge les résultats enrichis pour audit, partage ou analyse complémentaire.")

    c1, c2 = st.columns([1, 1])
    with c1:
        st.download_button(
            "Télécharger CSV (résultats enrichis)",
            data=nlp_df.to_csv(index=False).encode("utf-8"),
            file_name="insightia_resultats_enrichis.csv",
            mime="text/csv",
            use_container_width=True,
            key="ana_export_csv",
        )

    with c2:
        import io
        buf = io.BytesIO()
        try:
            nlp_df.to_parquet(buf, index=False)
            st.download_button(
                "Télécharger Parquet (recommandé)",
                data=buf.getvalue(),
                file_name="insightia_resultats_enrichis.parquet",
                mime="application/octet-stream",
                use_container_width=True,
                key="ana_export_parquet",
            )
        except Exception:
            st.info("Export Parquet indisponible (dépendances manquantes).")


def _footer_cta(nlp_df: Optional[pd.DataFrame]):
    st.divider()
    c1, c2 = st.columns([1, 1])

    with c1:
        if st.button("Changer de données", use_container_width=True):
            st.query_params["page"] = "start"
            st.rerun()

    with c2:
        if st.button("Page suivante : priorisation →", type="primary", use_container_width=True):
            if isinstance(nlp_df, pd.DataFrame) and not nlp_df.empty:
                st.session_state["ana_nlp_df"] = nlp_df
            st.query_params["page"] = "prioritization"
            st.rerun()


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

def render():
    _inject_premium_css()
    _h1_and_cta()

    df, origin = _get_current_df()
    if df is None or df.empty:
        colA, colB = st.columns([1.2, 0.8])
        with colA:
            st.info("Aucune donnée disponible. Importez un fichier dans **Importer** ou activez le mode Démo.")
            st.caption(f"Source détectée : {origin}")
        with colB:
            if st.button("Aller à Importer →", use_container_width=True):
                st.query_params["page"] = "start"
                st.rerun()
        return

    df = make_columns_unique(df)

    # Detect columns
    text_col = _best_col(["commentaire", "texte", "message", "verbatim", "feedback", "review", "content"], df.columns)
    source_col = _best_col(["canal", "source", "channel", "origin"], df.columns)
    date_col = _best_col(["date", "created_at", "created", "timestamp", "time"], df.columns)

    if text_col is None:
        st.error("Impossible de détecter la colonne de texte. Ajoute une colonne 'commentaire'/'texte' ou sélectionne-la à l’import.")
        st.caption(f"Dataset détecté depuis : {origin}")
        st_dataframe_safe(df.head(20), use_container_width=True, height=420)
        return

    # Optional configuration
    with st.expander("Configuration (optionnel)", expanded=False):
        st.caption("Ajustez les colonnes si nécessaire. Les valeurs sont mises à jour immédiatement.")
        a, b, c = st.columns(3)
        with a:
            text_col = st.selectbox("Colonne de texte", options=list(df.columns), index=list(df.columns).index(text_col))
        with b:
            if source_col is None:
                tmp = st.selectbox("Colonne source (optionnel)", options=["—"] + list(df.columns), index=0)
                source_col = None if tmp == "—" else tmp
            else:
                tmp = st.selectbox("Colonne source (optionnel)", options=["—"] + list(df.columns), index=(["—"] + list(df.columns)).index(source_col))
                source_col = None if tmp == "—" else tmp
        with c:
            if date_col is None:
                tmp = st.selectbox("Colonne date (optionnel)", options=["—"] + list(df.columns), index=0)
                date_col = None if tmp == "—" else tmp
            else:
                tmp = st.selectbox("Colonne date (optionnel)", options=["—"] + list(df.columns), index=(["—"] + list(df.columns)).index(date_col))
                date_col = None if tmp == "—" else tmp

    _method_note()

    # Filters
    filt_df, _, _ = _apply_filters(df, text_col=text_col, source_col=source_col, date_col=date_col)

    # Small perimeter KPIs (minimal, client-friendly)
    nb_empty_global = int(_is_empty_text(df[text_col]).sum())
    n_sources_active = int(filt_df[source_col].nunique()) if source_col and len(filt_df) else 0
    if date_col and "_dt" in filt_df.columns and len(filt_df) and filt_df["_dt"].notna().any():
        start_dt_disp = filt_df["_dt"].dropna().min()
        end_dt_disp = filt_df["_dt"].dropna().max()
    else:
        start_dt_disp, end_dt_disp = pd.NaT, pd.NaT

    c1, c2, c3 = st.columns(3)
    c1.metric("Messages (périmètre)", f"{len(filt_df):,}".replace(",", " "))
    c2.metric("Sources actives", int(n_sources_active))
    c3.metric("Messages vides (dataset)", int(nb_empty_global))
    if pd.notna(start_dt_disp) and pd.notna(end_dt_disp):
        st.caption(f"Période analysée : {start_dt_disp:%Y-%m-%d} → {end_dt_disp:%Y-%m-%d}")

    st.divider()

    # NLP section (button + caching)
    _card_header(
        "Structuration des retours",
        "Cette étape regroupe les messages pour faciliter la lecture par thématiques (sans prendre de décision).",
        badges=[("Analyse", "ix-badge-primary")],
    )
    _help("Clique pour structurer le périmètre filtré. Le résultat reste descriptif : il sert à comprendre.")

    st.session_state.setdefault("ana_nlp_cache_key", None)
    st.session_state.setdefault("ana_nlp_df", None)

    key = _hash_key(filt_df, text_col, source_col, date_col)

    run = st.button("Structurer les retours clients", type="primary", use_container_width=False, key="ana_run_nlp")

    nlp_df = st.session_state.get("ana_nlp_df")
    cache_key = st.session_state.get("ana_nlp_cache_key")

    if run or (isinstance(nlp_df, pd.DataFrame) and not nlp_df.empty and cache_key == key):
        if run or cache_key != key:
            with st.spinner("Analyse en cours…"):
                nlp_df = _run_nlp(filt_df, text_col=text_col)

            st.session_state["ana_nlp_df"] = nlp_df
            st.session_state["ana_nlp_cache_key"] = key

            # Persist (best effort)
            try:
                PERSIST_DIR.mkdir(exist_ok=True)
                nlp_df.to_parquet(PERSIST_FILE, index=False)
            except Exception:
                pass

        if not isinstance(nlp_df, pd.DataFrame) or nlp_df.empty:
            st.warning("Aucune ligne exploitable après filtrage (texte vide).")
            _footer_cta(None)
            return

        st.divider()

        # ✅ VALIDATED BLOCKS ONLY + CLIENT WORDING
        _bloc_indicateurs(nlp_df)
        st.divider()

        _bloc_thematiques(nlp_df)
        st.divider()

        _bloc_messages_non_rattaches(nlp_df)
        st.divider()

        _exports(nlp_df)
        _footer_cta(nlp_df)

    else:
        st.info("Applique ton périmètre, puis clique sur “Structurer les retours clients”.")
        _footer_cta(None)
