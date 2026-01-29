from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st
import altair as alt

from core.scoring import theme_table, backlog_from_theme_table, ImpactWeights

# ============================================================
# CONFIG
# ============================================================

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
PERSIST_NLP_FILE = DATA_DIR / "last_nlp.parquet"


# ============================================================
# STYLE (premium – structure V1)
# ============================================================

def _inject_css():
    st.markdown(
        """
<style>
:root{
  --bg:#070b14;
  --card:rgba(15,23,42,.75);
  --text:#e2e8f0;
  --muted:rgba(226,232,240,.7);
  --border:rgba(148,163,184,.18);
}
.stApp{
  background:
    radial-gradient(1200px 600px at 10% 0%, rgba(37,99,235,.18), transparent 45%),
    radial-gradient(900px 500px at 90% 10%, rgba(239,68,68,.14), transparent 55%),
    var(--bg);
  color:var(--text);
}
.ix-card{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:18px;
  padding:18px;
}
.ix-muted{ color:var(--muted); font-size:.95rem; line-height:1.45rem; }
[data-testid="stDataFrame"]{
  border-radius:16px;
  border:1px solid var(--border);
}
.stButton>button{
  border-radius:14px;
  font-weight:650;
}
</style>
""",
        unsafe_allow_html=True,
    )


def _card(title: str, subtitle: str):
    st.markdown(
        f"""
<div class="ix-card">
  <h3>{title}</h3>
  <p class="ix-muted">{subtitle}</p>
</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# DATA LOADING (safe)
# ============================================================

def _load_analysis() -> Optional[pd.DataFrame]:
    df = st.session_state.get("ana_nlp_df")
    if isinstance(df, pd.DataFrame) and not df.empty:
        return df

    if PERSIST_NLP_FILE.exists():
        try:
            df = pd.read_parquet(PERSIST_NLP_FILE)
            st.session_state["ana_nlp_df"] = df
            return df
        except Exception:
            return None
    return None


def _ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "theme" not in out.columns:
        out["theme"] = "Inconnu"
    if "blocking" not in out.columns:
        out["blocking"] = False
    if "sentiment" not in out.columns:
        out["sentiment"] = "Neutre"
    if "texte" not in out.columns:
        # fallback
        for c in ["commentaire", "verbatim", "message", "feedback", "text"]:
            if c in out.columns:
                out["texte"] = out[c].fillna("").astype(str)
                break
    if "texte" not in out.columns:
        out["texte"] = ""
    return out


# ============================================================
# WORDING CLIENT
# ============================================================

def _priority_label(p) -> str:
    return {"P0": "À traiter en urgence", "P1": "Important", "P2": "À planifier"}.get(str(p), "À qualifier")


def _severity_label(s) -> str:
    return {"S1": "Critique", "S2": "Sérieux", "S3": "Modéré"}.get(str(s), "—")


def _public_theme(val) -> str:
    t = str(val).strip().lower()
    if t in {"", "autre", "inconnu", "unknown", "other"}:
        return "Messages non rattachés"
    return str(val)


# ============================================================
# BACKLOG
# ============================================================

def _action_col(backlog_df: pd.DataFrame) -> str:
    """
    Dans certaines versions, backlog_from_theme_table renvoie 'theme', dans d’autres 'irritant'.
    On choisit automatiquement sans casser.
    """
    for c in ["theme", "irritant", "topic", "label", "cluster"]:
        if c in backlog_df.columns:
            return c
    # dernier recours : première colonne
    return backlog_df.columns[0]


def _build_backlog(df: pd.DataFrame, threshold: int, weights: ImpactWeights) -> pd.DataFrame:
    tt = theme_table(df)
    bl = backlog_from_theme_table(tt, weights=weights)

    # règle volume (P0 reste P0)
    if {"priorite_finale", "nb"}.issubset(bl.columns):
        mask = bl["priorite_finale"].astype(str).str.upper() != "P0"
        bl.loc[mask & (bl["nb"] >= threshold), "priorite_finale"] = "P1"
        bl.loc[mask & (bl["nb"] < threshold), "priorite_finale"] = "P2"

    return bl


def _public_view(bl: pd.DataFrame) -> pd.DataFrame:
    action_c = _action_col(bl)

    v = pd.DataFrame()
    v["Action"] = bl[action_c].apply(_public_theme)

    # priorité / sévérité
    if "priorite_finale" in bl.columns:
        v["Priorité"] = bl["priorite_finale"].apply(_priority_label)
    else:
        v["Priorité"] = "À qualifier"

    if "severite_finale" in bl.columns:
        v["Sévérité"] = bl["severite_finale"].apply(_severity_label)
    else:
        v["Sévérité"] = "—"

    # colonnes client-friendly (si dispo)
    if "nb" in bl.columns:
        v["Volume"] = pd.to_numeric(bl["nb"], errors="coerce").fillna(0).astype(int)
    if "nb_blocking" in bl.columns:
        v["Situations bloquantes"] = pd.to_numeric(bl["nb_blocking"], errors="coerce").fillna(0).astype(int)
    if "part_neg" in bl.columns:
        v["Part de retours négatifs (%)"] = (pd.to_numeric(bl["part_neg"], errors="coerce").fillna(0.0) * 100).round(0).astype(int)
    if "impact_score" in bl.columns:
        v["Impact estimé"] = pd.to_numeric(bl["impact_score"], errors="coerce").fillna(0.0).round(2)
    if "recommandation" in bl.columns:
        v["Direction proposée"] = bl["recommandation"].fillna("").astype(str)

    # tri simple et stable (sans dépendre du wording)
    order = {"À traiter en urgence": 0, "Important": 1, "À planifier": 2, "À qualifier": 9}
    v["_prio"] = v["Priorité"].map(order).fillna(9).astype(int)
    v = v.sort_values(["_prio"], ascending=True).drop(columns=["_prio"])

    return v


# ============================================================
# PREUVES
# ============================================================

def _examples(df: pd.DataFrame, action_public: str, k: int) -> pd.DataFrame:
    d = df.copy()

    if action_public == "Messages non rattachés":
        mask = d["theme"].fillna("").astype(str).str.strip().str.lower().isin(["", "autre", "inconnu", "unknown", "other"])
        d = d[mask]
    else:
        d = d[d["theme"].astype(str) == str(action_public)]

    if d.empty:
        return pd.DataFrame(columns=["Message", "Bloquant", "Tonalité"])

    # worst first
    d["_b"] = d["blocking"].fillna(False).astype(int)
    d["_n"] = (d["sentiment"].fillna("") == "Négatif").astype(int)
    d = d.sort_values(["_b", "_n"], ascending=[False, False])

    out = pd.DataFrame()
    out["Message"] = d["texte"].fillna("").astype(str).head(int(k))
    out["Bloquant"] = d["blocking"].fillna(False).astype(bool).map({True: "Oui", False: "Non"}).head(int(k))
    out["Tonalité"] = d["sentiment"].fillna("—").astype(str).head(int(k))
    return out


# ============================================================
# (Optional) Charts — simple and clean
# ============================================================

def _chart_priority(view: pd.DataFrame) -> None:
    if view.empty or "Priorité" not in view.columns:
        return
    d = view["Priorité"].value_counts().reset_index()
    d.columns = ["Priorité", "Actions"]
    ch = (
        alt.Chart(d)
        .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
        .encode(
            x=alt.X("Priorité:N", sort=None, title="Priorité"),
            y=alt.Y("Actions:Q", title="Nombre d’actions"),
            tooltip=["Priorité", "Actions"],
        )
        .properties(height=240)
    )
    st.altair_chart(ch, use_container_width=True)


# ============================================================
# PAGE
# ============================================================

def render():
    _inject_css()

    # Header (structure V1)
    left, right = st.columns([4, 1.2], vertical_alignment="top")
    with left:
        st.markdown("# Priorisez les actions")
        st.caption("Passez de l’analyse à un plan d’actions clair et défendable.")
    with right:
        if st.button("← Retour à l’analyse", use_container_width=True):
            st.query_params["page"] = "analysis"
            st.rerun()

    df = _load_analysis()
    if df is None:
        st.warning("Aucune analyse disponible.")
        if st.button("Aller à l’analyse →", type="primary", use_container_width=True):
            st.query_params["page"] = "analysis"
            st.rerun()
        return

    df = _ensure_cols(df)

    _card(
        "Ce que vous voyez ici",
        "Chaque ligne correspond à une action concrète, priorisée à partir des retours clients. "
        "Les preuves associées permettent de comprendre et d’expliquer chaque décision.",
    )

    # Settings
    st.divider()
    st.subheader("Réglages de priorisation")

    c1, c2, c3 = st.columns(3)
    with c1:
        threshold = st.number_input("Seuil de volume", 1, 100000, 100, 10)
    with c2:
        w_block = st.slider("Poids des situations bloquantes", 0.0, 1.0, 0.45, 0.05)
    with c3:
        w_neg = st.slider("Poids de l’insatisfaction", 0.0, 1.0, 0.25, 0.05)

    w_vol = max(0.0, 1.0 - (w_block + w_neg))
    weights = ImpactWeights(w_volume=w_vol, w_blocking=w_block, w_neg=w_neg)

    bl = _build_backlog(df, int(threshold), weights)
    if not isinstance(bl, pd.DataFrame) or bl.empty:
        st.info("Le backlog est vide pour ce périmètre.")
        return

    view = _public_view(bl)

    # KPI row
    st.divider()
    k1, k2, k3 = st.columns(3)
    k1.metric("Actions identifiées", len(view))
    if "Priorité" in view.columns:
        k2.metric("Urgentes", int((view["Priorité"] == "À traiter en urgence").sum()))
        k3.metric("Importantes", int((view["Priorité"] == "Important").sum()))
    else:
        k2.metric("Urgentes", "—")
        k3.metric("Importantes", "—")

    # chart
    _chart_priority(view)

    # Table
    st.divider()
    st.subheader("Backlog priorisé")
    st.dataframe(view, use_container_width=True, height=520)

    st.download_button(
        "Télécharger le backlog (CSV)",
        data=view.to_csv(index=False).encode("utf-8"),
        file_name="insightia_backlog.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # Proofs
    st.divider()
    st.subheader("Preuves issues des retours clients")

    if view.empty or "Action" not in view.columns:
        st.info("Aucune action disponible.")
        return

    action = st.selectbox("Action sélectionnée", view["Action"].astype(str).tolist(), index=0)
    k = st.slider("Nombre d’exemples", 3, 20, 8)

    ex = _examples(df, action, int(k))
    st.dataframe(ex, use_container_width=True, height=380)

    st.download_button(
        "Télécharger ces preuves (CSV)",
        data=ex.to_csv(index=False).encode("utf-8"),
        file_name="insightia_preuves.csv",
        mime="text/csv",
        use_container_width=True,
    )
