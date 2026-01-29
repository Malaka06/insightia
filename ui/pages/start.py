from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, List
import html as _html

import pandas as pd
import streamlit as st

DATA_DIR = Path("data")
SUPPORTED_EXTS = {".csv", ".xlsx", ".xls", ".ods"}


def _read_csv_fallback(path_or_file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    try:
        try:
            return pd.read_csv(path_or_file, encoding="utf-8"), None
        except Exception:
            if hasattr(path_or_file, "seek"):
                path_or_file.seek(0)
            return pd.read_csv(path_or_file, encoding="latin-1"), None
    except Exception:
        return None, "Impossible de lire le fichier CSV (encodage ou format invalide)."


def read_table_from_path(path: Path) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    try:
        ext = path.suffix.lower()

        if ext == ".csv":
            return _read_csv_fallback(path)

        if ext in {".xlsx", ".xls"}:
            return pd.read_excel(path), None

        if ext == ".ods":
            try:
                return pd.read_excel(path, engine="odf"), None
            except Exception:
                return None, "Le format .ods n’est pas supporté ici. Exportez en .xlsx ou .csv."

        return None, "Format non supporté. Utilisez CSV ou XLSX."
    except Exception:
        return None, "Le fichier n’a pas pu être lu."


def read_table_from_upload(uploaded) -> Tuple[Optional[pd.DataFrame], Optional[str], str]:
    if uploaded is None:
        return None, None, ""

    name = getattr(uploaded, "name", "fichier")
    ext = Path(name).suffix.lower()

    try:
        if ext == ".csv":
            df, err = _read_csv_fallback(uploaded)
            return df, err, name

        if ext in {".xlsx", ".xls"}:
            return pd.read_excel(uploaded), None, name

        if ext == ".ods":
            try:
                return pd.read_excel(uploaded, engine="odf"), None, name
            except Exception:
                return None, "Le format .ods n’est pas supporté ici. Exportez en .xlsx ou .csv.", name

        return None, "Format non supporté. Utilisez CSV ou XLSX.", name
    except Exception:
        return None, "Le fichier n’a pas pu être lu. Vérifiez le format.", name


def _guess_column(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    if df is None or df.empty:
        return None
    lowered = {str(c).lower(): str(c) for c in df.columns}
    for kw in keywords:
        for c_low, original in lowered.items():
            if kw in c_low:
                return original
    return None


def guess_text_column(df: pd.DataFrame) -> Optional[str]:
    preferred = ["verbatim", "commentaire", "comment", "feedback", "texte", "avis", "message", "description", "content"]
    col = _guess_column(df, preferred)
    if col:
        return col

    for c in df.columns:
        s = df[c]
        if s.dtype == "object":
            sample = s.dropna().astype(str).str.strip()
            if (sample != "").any():
                return str(c)
    return None


def guess_date_column(df: pd.DataFrame) -> Optional[str]:
    return _guess_column(df, ["date", "created", "timestamp", "time", "jour", "mois"])


def guess_channel_column(df: pd.DataFrame) -> Optional[str]:
    return _guess_column(df, ["canal", "channel", "source", "origine", "platform", "plateforme"])


def guess_score_column(df: pd.DataFrame) -> Optional[str]:
    return _guess_column(df, ["csat", "nps", "score", "rating", "note", "satisfaction"])


def guess_id_column(df: pd.DataFrame) -> Optional[str]:
    return _guess_column(df, ["id", "ticket", "case", "reference", "référence"])


def _date_range(df: pd.DataFrame, date_col: Optional[str]) -> Optional[Tuple[str, str]]:
    if not date_col or date_col not in df.columns:
        return None
    dt = pd.to_datetime(df[date_col], errors="coerce")
    if not dt.notna().any():
        return None
    return dt.min().date().isoformat(), dt.max().date().isoformat()


def _channels_count(df: pd.DataFrame, channel_col: Optional[str]) -> Optional[int]:
    if not channel_col or channel_col not in df.columns:
        return None
    return int(df[channel_col].fillna("Non renseigné").astype(str).nunique())


def _list_demo_files() -> List[Path]:
    if not DATA_DIR.exists():
        return []
    demos: List[Path] = []
    for p in DATA_DIR.iterdir():
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS and p.name.lower().startswith("demo"):
            demos.append(p)
    return sorted(demos, key=lambda x: x.name.lower())


def _inject_css() -> None:
    st.markdown(
        """
<style>
.ix-start{
  --ix-card: rgba(15,23,42,.55);
  --ix-card2: rgba(15,23,42,.35);
  --ix-border: rgba(148,163,184,.18);
  --ix-muted: #94a3b8;
  --ix-text: #e2e8f0;
  --ix-shadow: 0 14px 30px rgba(2,6,23,.25);
  --ix-red: rgba(239,68,68,.90);
}

.ix-start .ix-hero{
  background: var(--ix-card);
  border: 1px solid var(--ix-border);
  border-radius: 18px;
  padding: 18px 18px;
  box-shadow: var(--ix-shadow);
  backdrop-filter: blur(10px);
}

.ix-start .ix-title{
  font-size: 2.35rem;
  font-weight: 850;
  color: var(--ix-text);
  margin: 2px 0 8px 0;
  letter-spacing: -0.02em;
}

.ix-start .ix-sub{
  color: var(--ix-muted);
  line-height: 1.7rem;
  font-size: 1.10rem;
  max-width: 90ch;
}

.ix-start .ix-meta{
  color: rgba(148,163,184,.85);
  font-size: 1.00rem;
  margin-top: 10px;
}

.ix-start .ix-card2{
  background: var(--ix-card2);
  border: 1px solid var(--ix-border);
  border-radius: 18px;
  padding: 16px 16px;
}

.ix-start .ix-h2{
  font-size: 1.60rem;
  font-weight: 820;
  color: var(--ix-text);
  margin: 4px 0 8px 0;
}

.ix-start .ix-label{
  color: rgba(148,163,184,.9);
  font-weight: 650;
  margin-top: 12px;
  font-size: 1.05rem;
}

.ix-start .ix-small{
  color: var(--ix-muted);
  font-size: 1.0rem;
  line-height: 1.55rem;
}

.ix-start .ix-redbox{
  border: 1px solid var(--ix-red);
  border-radius: 14px;
  padding: 14px 14px;
  background: rgba(255,255,255,0.02);
}

.ix-start .ix-redbox-title{
  color: #fff;
  font-weight: 750;
  font-size: 15px;
  margin-bottom: 10px;
}

.ix-start .ix-table{
  width: 100%;
  border-collapse: collapse;
}

.ix-start .ix-table td{
  padding: 9px 0;
  color: #fff;
  font-size: 15px;
  border-top: 1px solid rgba(255,255,255,0.06);
}

.ix-start .ix-table tr:first-child td{
  border-top: none;
}

.ix-start .ix-table td:last-child{
  text-align: right;
  color: rgba(255,255,255,0.70);
  white-space: nowrap;
}

.ix-start .ix-preview{
  width: 100%;
  border: 1px solid var(--ix-red);
  border-radius: 14px;
  border-collapse: separate;
  border-spacing: 0;
  overflow: hidden;
  background: rgba(255,255,255,0.02);
}

.ix-start .ix-preview th{
  text-align: left;
  font-size: 14px;
  font-weight: 700;
  color: rgba(255,255,255,0.78);
  padding: 12px 14px;
  background: rgba(255,255,255,0.03);
}

.ix-start .ix-preview td{
  padding: 12px 14px;
  font-size: 15px;
  color: #fff;
  border-top: 1px solid rgba(255,255,255,0.06);
  vertical-align: top;
}

.ix-start .ix-preview td.meta{
  color: rgba(255,255,255,0.68);
  white-space: nowrap;
}

/* Barre du selectbox (dans la page) */
.ix-start [data-testid="stSelectbox"] div[role="combobox"]{
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(239,68,68,0.90) !important;
  border-radius: 14px !important;
  padding: 10px 14px !important;
  box-shadow: none !important;
}

.ix-start [data-testid="stSelectbox"] div[role="combobox"] span,
.ix-start [data-testid="stSelectbox"] div[role="combobox"] input{
  color: #ffffff !important;
  font-size: 15px !important;
  font-weight: 600 !important;
}

.ix-start [data-testid="stSelectbox"] svg{
  fill: #ffffff !important;
}

/* Boutons */
.ix-start .stButton > button{
  border-radius: 14px !important;
  padding: 11px 14px !important;
  font-weight: 680 !important;
}

/* Menu du selectbox (portal BaseWeb : hors wrapper) */
div[data-baseweb="popover"]{
  background: transparent !important;
}

div[data-baseweb="menu"]{
  background: rgba(2,6,23,0.97) !important;
  border: 1px solid rgba(239,68,68,0.55) !important;
  border-radius: 14px !important;
  box-shadow: 0 20px 40px rgba(0,0,0,0.6) !important;
  padding: 6px 0 !important;
}

li[role="option"]{
  background: transparent !important;
  color: #ffffff !important;
  font-size: 14px !important;
  padding: 10px 14px !important;
}

li[role="option"]:hover{
  background: rgba(239,68,68,0.14) !important;
}

li[aria-selected="true"]{
  background: rgba(239,68,68,0.20) !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def _hero() -> None:
    st.markdown(
        """
<div class="ix-start">
  <div class="ix-hero">
    <div class="ix-title">Charger vos retours clients</div>
    <div class="ix-sub">
      Importez vos retours (tickets, avis, enquêtes). InsightIA structure la voix du client en thèmes exploitables
      afin d’en faciliter la lecture et l’analyse.
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _dataset_micro_description(df: Optional[pd.DataFrame], origin_label: str) -> str:
    if df is None or df.empty:
        return f"Aperçu : {origin_label} · Lecture disponible après chargement"

    text_col = guess_text_column(df)
    date_col = guess_date_column(df)
    ch_col = guess_channel_column(df)
    score_col = guess_score_column(df)

    parts = [origin_label, f"{len(df):,} retours".replace(",", " ")]
    dr = _date_range(df, date_col)
    if dr:
        parts.append(f"Période {dr[0]} → {dr[1]}")
    ch = _channels_count(df, ch_col)
    if ch is not None:
        parts.append(f"Canaux {ch}")
    if score_col:
        parts.append("Score détecté")
    if text_col:
        parts.append(f"Texte : {text_col}")
    return "Aperçu : " + " · ".join(parts)


def _render_structure_table(rows: List[Tuple[str, str]]) -> None:
    trs = "".join([f"<tr><td>{_html.escape(k)}</td><td>{_html.escape(v)}</td></tr>" for k, v in rows])
    st.markdown(
        f"""
<div class="ix-start">
  <div class="ix-redbox">
    <div class="ix-redbox-title">Structure des données · Champs détectés</div>
    <table class="ix-table">{trs}</table>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_preview_table(
    df: pd.DataFrame,
    text_col: str,
    channel_col: Optional[str],
    score_col: Optional[str],
    n: int = 5,
) -> None:
    if text_col not in df.columns:
        st.markdown(
            "<div class='ix-start'><div class='ix-small'>Aucun champ texte détecté : aperçu indisponible.</div></div>",
            unsafe_allow_html=True,
        )
        return

    cols = [text_col]
    headers = ["Retour client"]

    if channel_col and channel_col in df.columns:
        cols.append(channel_col)
        headers.append("Canal")

    if score_col and score_col in df.columns:
        cols.append(score_col)
        headers.append("Score")

    sample = df[cols].head(n).copy()
    th = "".join([f"<th>{_html.escape(h)}</th>" for h in headers])

    rows_html: List[str] = []
    for _, r in sample.iterrows():
        text = str(r[text_col]) if pd.notna(r[text_col]) else ""
        text = (_html.escape(text.strip()) or "—")
        tds = [f"<td>{text}</td>"]

        if channel_col and channel_col in sample.columns:
            v = str(r[channel_col]) if pd.notna(r[channel_col]) else "—"
            tds.append(f"<td class='meta'>{_html.escape(v)}</td>")

        if score_col and score_col in sample.columns:
            v = str(r[score_col]) if pd.notna(r[score_col]) else "—"
            tds.append(f"<td class='meta'>{_html.escape(v)}</td>")

        rows_html.append("<tr>" + "".join(tds) + "</tr>")

    st.markdown(
        f"""
<div class="ix-start">
  <table class="ix-preview">
    <thead><tr>{th}</tr></thead>
    <tbody>{''.join(rows_html)}</tbody>
  </table>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_dataset_summary(df: pd.DataFrame, source_label: str) -> None:
    id_col = guess_id_column(df)
    date_col = guess_date_column(df)
    ch_col = guess_channel_column(df)
    score_col = guess_score_column(df)
    text_col = guess_text_column(df)

    rows: List[Tuple[str, str]] = []
    if id_col:
        rows.append(("Identifiant", id_col))
    if date_col:
        rows.append(("Date", date_col))
    if ch_col:
        rows.append(("Canal", ch_col))
    if score_col:
        rows.append(("Score de satisfaction", score_col))
    if text_col:
        rows.append(("Texte client", text_col))

    st.markdown("<div class='ix-start'><div class='ix-card2'>", unsafe_allow_html=True)
    st.markdown("<div class='ix-h2'>Vue d’ensemble des données importées</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='ix-small'>Vérifiez que les données chargées sont cohérentes avant de lancer l’analyse.</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Retours", f"{len(df):,}".replace(",", " "))
    c2.metric("Champs", f"{len(df.columns)}")
    c3.metric("Origine", source_label)

    st.markdown("<div class='ix-label'>Structure des données</div>", unsafe_allow_html=True)
    if rows:
        _render_structure_table(rows)
    else:
        st.markdown(
            "<div class='ix-small'>Aucun champ standard détecté automatiquement. Vous pourrez sélectionner les champs à l’étape suivante.</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='ix-label'>Texte analysé</div>", unsafe_allow_html=True)
    if text_col:
        st.markdown(
            f"<div class='ix-small'><strong>{_html.escape(text_col)}</strong> — champ utilisé pour analyser la parole client.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='ix-small'>Aucune colonne texte détectée. L’analyse nécessite un champ de verbatim.</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='ix-label' style='margin-top:14px;'>Aperçu des retours clients</div>", unsafe_allow_html=True)
    st.markdown("<div class='ix-small'>Échantillon représentatif des données chargées.</div>", unsafe_allow_html=True)

    if text_col:
        _render_preview_table(df, text_col=text_col, channel_col=ch_col, score_col=score_col, n=5)
    else:
        st.markdown("<div class='ix-small'>Aperçu indisponible : aucun champ texte détecté.</div>", unsafe_allow_html=True)

    with st.expander("Afficher le tableau complet (aperçu)", expanded=False):
        st.dataframe(df.head(50), use_container_width=True)

    st.markdown("</div></div>", unsafe_allow_html=True)


def render_start() -> None:
    st.session_state.setdefault("dataset_df", None)
    st.session_state.setdefault("dataset_source", None)
    st.session_state.setdefault("dataset_name", None)

    _inject_css()
    _hero()

    tab_demo, tab_upload = st.tabs(["Démo (exemple)", "Mes données"])

    with tab_demo:
        demo_files = _list_demo_files()

        st.markdown("<div class='ix-start'><div class='ix-label'>Jeu de données (démo)</div></div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='ix-start'><div class='ix-small'>Sélectionnez un exemple pour découvrir le fonctionnement d’InsightIA.</div></div>",
            unsafe_allow_html=True,
        )

        if demo_files:
            labels = [p.name for p in demo_files]
            picked = st.selectbox("", labels, index=0, key="start_demo_picker", label_visibility="collapsed")

            st.markdown(
                f"<div class='ix-start'><div class='ix-meta'>Aperçu : {_html.escape(picked)} · prêt à analyser</div></div>",
                unsafe_allow_html=True,
            )

            c1, c2, c3 = st.columns(3)
            with c1:
                load_demo = st.button("Charger l’exemple", use_container_width=True, key="start_demo_load")
            with c2:
                reset_demo = st.button("Réinitialiser", use_container_width=True, key="start_demo_reset")
            with c3:
                go_analysis_demo = st.button("Analyser", type="primary", use_container_width=True, key="start_demo_go")

            if reset_demo:
                st.session_state["dataset_df"] = None
                st.session_state["dataset_source"] = None
                st.session_state["dataset_name"] = None
                st.rerun()

            if load_demo:
                path = next(p for p in demo_files if p.name == picked)
                df, err = read_table_from_path(path)
                if err:
                    st.error(err)
                elif df is None or df.empty:
                    st.warning("Données chargées, mais aucune ligne n’a été détectée.")
                else:
                    st.session_state["dataset_df"] = df
                    st.session_state["dataset_source"] = "demo"
                    st.session_state["dataset_name"] = picked
                    st.success("Exemple chargé avec succès.")

            if st.session_state.get("dataset_source") == "demo" and st.session_state.get("dataset_df") is not None:
                df = st.session_state["dataset_df"]
                desc = _dataset_micro_description(df, "Exemple")
                st.markdown(f"<div class='ix-start'><div class='ix-meta'>{_html.escape(desc)}</div></div>", unsafe_allow_html=True)
                st.divider()
                _render_dataset_summary(df, source_label="Exemple")

            if go_analysis_demo:
                df_ok = st.session_state.get("dataset_df") is not None and not st.session_state["dataset_df"].empty
                if not df_ok:
                    st.warning("Veuillez charger un exemple avant de lancer l’analyse.")
                else:
                    st.query_params["page"] = "analysis"
                    st.rerun()
        else:
            st.info("Aucun fichier de démonstration trouvé dans data/ (demo_*.csv ou demo_*.xlsx).")

    with tab_upload:
        st.markdown("<div class='ix-start'><div class='ix-label'>Importer un fichier</div></div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='ix-start'><div class='ix-small'>Formats acceptés : CSV, XLSX · 1 ligne = 1 retour client</div></div>",
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            "",
            type=["csv", "xlsx", "xls", "ods"],
            key="start_upload_file",
            label_visibility="collapsed",
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            load_file = st.button("Charger le fichier", use_container_width=True, key="start_upload_load")
        with c2:
            reset_file = st.button("Réinitialiser", use_container_width=True, key="start_upload_reset")
        with c3:
            go_analysis_upload = st.button("Analyser", type="primary", use_container_width=True, key="start_upload_go")

        if reset_file:
            st.session_state["dataset_df"] = None
            st.session_state["dataset_source"] = None
            st.session_state["dataset_name"] = None
            st.rerun()

        if load_file:
            df, err, filename = read_table_from_upload(uploaded)
            if err:
                st.error(err)
            elif df is None or df.empty:
                st.warning("Données chargées, mais aucune ligne n’a été détectée.")
            else:
                st.session_state["dataset_df"] = df
                st.session_state["dataset_source"] = "upload"
                st.session_state["dataset_name"] = filename or "fichier"
                st.success("Fichier chargé avec succès.")

        if st.session_state.get("dataset_source") == "upload" and st.session_state.get("dataset_df") is not None:
            df = st.session_state["dataset_df"]
            desc = _dataset_micro_description(df, "Import")
            st.markdown(f"<div class='ix-start'><div class='ix-meta'>{_html.escape(desc)}</div></div>", unsafe_allow_html=True)
            st.divider()
            _render_dataset_summary(df, source_label="Import")

        if go_analysis_upload:
            df_ok = st.session_state.get("dataset_df") is not None and not st.session_state["dataset_df"].empty
            if not df_ok:
                st.warning("Veuillez charger un fichier avant de lancer l’analyse.")
            else:
                st.query_params["page"] = "analysis"
                st.rerun()


def render():
    render_start()
