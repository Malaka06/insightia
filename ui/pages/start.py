from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import streamlit as st

DATA_DIR = Path("data")
SUPPORTED_EXTS = {".csv", ".xlsx", ".xls", ".ods"}


# ---------------------------
# Lecture fichiers (safe)
# ---------------------------

def _read_csv_fallback(path_or_file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    try:
        try:
            return pd.read_csv(path_or_file, encoding="utf-8"), None
        except Exception:
            if hasattr(path_or_file, "seek"):
                path_or_file.seek(0)
            return pd.read_csv(path_or_file, encoding="latin-1"), None
    except Exception:
        return None, "Impossible de lire le fichier CSV."


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
                return None, "Le format .ods n’est pas pris en charge ici. Exportez en .xlsx ou .csv."

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
                return None, "Le format .ods n’est pas pris en charge ici. Exportez en .xlsx ou .csv.", name

        return None, "Format non supporté. Utilisez CSV ou XLSX.", name
    except Exception:
        return None, "Le fichier n’a pas pu être lu. Vérifiez le format.", name


# ---------------------------
# Aides preview
# ---------------------------

def guess_text_column(df: pd.DataFrame) -> Optional[str]:
    if df is None or df.empty:
        return None

    preferred = ["verbatim", "commentaire", "comment", "feedback", "texte", "avis", "message"]
    lowered = {str(c).lower(): str(c) for c in df.columns}

    for key in preferred:
        for col_l, original in lowered.items():
            if key in col_l:
                return original

    # fallback: first object column with non-empty values
    for c in df.columns:
        s = df[c]
        if s.dtype == "object":
            sample = s.dropna().astype(str).head(50)
            if len(sample) > 0:
                return str(c)

    return None


def render_preview(df: pd.DataFrame, source_label: str, dataset_name: str) -> None:
    st.markdown("<div class='data-preview'>", unsafe_allow_html=True)
    st.markdown("### Résumé du jeu de données")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Lignes", f"{len(df):,}".replace(",", " "))
    with c2:
        st.metric("Colonnes", f"{len(df.columns)}")
    with c3:
        st.metric("Source", source_label)

    cols = [str(c) for c in df.columns.tolist()]
    st.markdown("**Champs détectés**")
    st.write(", ".join(cols[:40]) + ("…" if len(cols) > 40 else ""))

    text_col = guess_text_column(df)
    if text_col:
        st.markdown("**Colonne de verbatim utilisée**")
        st.write(text_col)

        examples = df[text_col].dropna().astype(str).head(5).tolist()
        st.markdown("**Extraits de retours clients**")
        if examples:
            for e in examples:
                st.write(f"– {e[:260]}")
        else:
            st.write("Aucun extrait disponible.")
    else:
        st.info("Aucune colonne de texte détectée automatiquement. Vous pourrez la sélectionner à l’étape Analyse.")

    st.markdown("**Extrait des données**")
    st.dataframe(df.head(12), use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)


def _list_demo_files() -> list[Path]:
    if not DATA_DIR.exists():
        return []

    demos = []
    for p in DATA_DIR.iterdir():
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS and p.name.lower().startswith("demo"):
            demos.append(p)
    return sorted(demos, key=lambda x: x.name.lower())


# ---------------------------
# Page
# ---------------------------

def render_start() -> None:
    st.session_state.setdefault("dataset_df", None)
    st.session_state.setdefault("dataset_source", None)  # "demo" | "upload"
    st.session_state.setdefault("dataset_name", None)
    st.markdown("<div class='page-start'>", unsafe_allow_html=True)


    # Light hero (premium)
    st.markdown(
        """
        <section class="start-hero start-page">
          <div class="start-hero-inner">
            <div class="start-hero-kicker">Import</div>
            <h2 class="start-hero-title">Importez vos retours clients</h2>
            <p class="start-hero-sub">
    Importez vos retours (NPS, tickets, avis). INSIGHTIA regroupe, comprend et classe les irritants en thèmes métier.
    En quelques minutes, vous obtenez une synthèse claire et un backlog priorisé (P0/P1) prêt à exécuter.
    </p>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    tab_demo, tab_upload = st.tabs(["Essayer un exemple", "Importer mes données"])

    # ---------------- DEMO ----------------
    with tab_demo:
        demo_files = _list_demo_files()

        if not demo_files:
            st.warning("Aucun fichier d’exemple trouvé dans data/. Ajoutez un fichier demo_*.csv ou demo_*.xlsx.")
        else:
            labels = [p.name for p in demo_files]
            picked = st.selectbox(
                "Jeu de données d’exemple",
                labels,
                index=0,
                key="start_demo_picker",
            )

            # Actions: secondary / ghost / primary (premium hierarchy)
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                load_demo = st.button("Charger les données", use_container_width=True, key="start_demo_load")
            with c2:
                clear_demo = st.button("Réinitialiser", use_container_width=True, key="start_demo_clear")
            with c3:
                go_analysis_demo = st.button("Lancer l’analyse", type="primary", use_container_width=True, key="start_demo_go")

            if clear_demo:
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
                    st.warning("Données chargées, mais aucune ligne n’a été trouvée.")
                    st.session_state["dataset_df"] = df
                    st.session_state["dataset_source"] = "demo"
                    st.session_state["dataset_name"] = picked
                else:
                    st.session_state["dataset_df"] = df
                    st.session_state["dataset_source"] = "demo"
                    st.session_state["dataset_name"] = picked
                    st.success("✔ Données chargées avec succès.")

            if st.session_state.get("dataset_source") == "demo" and st.session_state.get("dataset_df") is not None:
                df = st.session_state["dataset_df"]
                # Small confidence line (premium reassurance)
                st.caption(f" Données prêtes · {len(df):,} retours détectés".replace(",", " "))
                render_preview(df, "Exemple", st.session_state.get("dataset_name") or "Exemple")

            if go_analysis_demo:
                st.query_params["page"] = "analysis"
                st.rerun()

    # ---------------- UPLOAD ----------------
    with tab_upload:
        st.markdown(
            """
            <div class='start-guidelines'>
              <p class='guidelines-title'>Préparer vos données</p>
              <p class='guidelines-text'>
                Vos données peuvent venir de NPS, tickets support, avis ou enquêtes.
                Une seule colonne contenant les verbatims suffit pour démarrer.
              </p>
              <ul class='guidelines-list'>
                <li><strong>Verbatim</strong> (recommandé)</li>
                <li>Source (optionnel)</li>
                <li>Date (optionnel)</li>
                <li>Segment / Client (optionnel)</li>
              </ul>
              <p class='guidelines-foot'>Même si certaines informations sont absentes, l’analyse peut démarrer.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            "Importer un fichier (CSV ou XLSX)",
            type=["csv", "xlsx", "xls", "ods"],
            key="start_upload_file",
        )

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            load_file = st.button("Importer", use_container_width=True, key="start_upload_load")
        with c2:
            clear_file = st.button("Réinitialiser", use_container_width=True, key="start_upload_clear")
        with c3:
            go_analysis_upload = st.button("Lancer l’analyse", type="primary", use_container_width=True, key="start_upload_go")

        if clear_file:
            st.session_state["dataset_df"] = None
            st.session_state["dataset_source"] = None
            st.session_state["dataset_name"] = None
            st.rerun()

        if load_file:
            df, err, filename = read_table_from_upload(uploaded)
            if err:
                st.error(err)
            elif df is None or df.empty:
                st.warning("Données importées, mais aucune ligne n’a été trouvée.")
                st.session_state["dataset_df"] = df
                st.session_state["dataset_source"] = "upload"
                st.session_state["dataset_name"] = filename or "fichier"
            else:
                st.session_state["dataset_df"] = df
                st.session_state["dataset_source"] = "upload"
                st.session_state["dataset_name"] = filename or "fichier"
                st.success("✔ Données importées avec succès.")

        if st.session_state.get("dataset_source") == "upload" and st.session_state.get("dataset_df") is not None:
            df = st.session_state["dataset_df"]
            st.caption(f"✅ Données prêtes · {len(df):,} retours détectés".replace(",", " "))
            render_preview(df, "Fichier", st.session_state.get("dataset_name") or "Fichier")

        if go_analysis_upload:
            st.query_params["page"] = "analysis"
            st.rerun()
# ============================================================
# Entrée publique standard
# ============================================================

def render():
    render_start()
