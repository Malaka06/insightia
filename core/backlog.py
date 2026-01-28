import sys
from pathlib import Path
import streamlit as st
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="INSIGHTIA — Backlog", layout="wide")
st.title("3) Backlog décisionnel")

CACHE_DIR = ROOT / "data" / "_cache"
TOPICS_CACHE = CACHE_DIR / "topics_cache.csv"


def load_topics_cache() -> pd.DataFrame | None:
    if TOPICS_CACHE.exists():
        try:
            return pd.read_csv(TOPICS_CACHE)
        except Exception:
            return None
    return None


# 1) récup session, sinon cache
df = st.session_state.get("topics_df")
if df is None:
    cached = load_topics_cache()
    if cached is not None and len(cached) > 0:
        st.warning("Session perdue : je recharge l'analyse depuis le cache ✅")
        st.session_state["topics_df"] = cached
        df = cached
    else:
        st.warning("Va d’abord sur **2) Analyse** (ou relance l'analyse).")
        st.stop()

df = df.copy()

# 2) backlog key = theme
df["backlog_key"] = df["theme"].astype(str)

# 3) agrégation
bl = (
    df.groupby("backlog_key", dropna=False)
      .agg(
          nb=("backlog_key", "size"),
          blocking=("blocking", "sum"),
          neg_rate=("sentiment", lambda s: float((s == "Négatif").mean())),
          part_low=("low_confidence", "mean"),
          sample=("texte", lambda s: str(s.iloc[0])[:180] if len(s) else "")
      )
      .reset_index()
      .rename(columns={"backlog_key": "irritant"})
)

bl["blocking_rate"] = bl["blocking"] / bl["nb"].clip(lower=1)
bl["impact_score"] = bl["nb"] * (1 + 2 * bl["blocking_rate"]) * (1 + bl["neg_rate"])

def prio_sugg(row) -> str:
    if row["blocking"] >= max(2, 0.05 * row["nb"]):
        return "P0"
    if row["neg_rate"] >= 0.35 or row["impact_score"] >= bl["impact_score"].quantile(0.75):
        return "P1"
    return "P2"

def sev_sugg(row) -> str:
    if row["blocking"] > 0:
        return "Critique"
    if row["neg_rate"] >= 0.35:
        return "Haute"
    return "Moyenne"

bl["priorite_suggeree"] = bl.apply(prio_sugg, axis=1)
bl["severite_suggeree"] = bl.apply(sev_sugg, axis=1)
bl["priorite_finale"] = bl["priorite_suggeree"]
bl["severite_finale"] = bl["severite_suggeree"]

bl = bl.sort_values("impact_score", ascending=False)

st.subheader("Backlog (trié par impact)")
st.caption("Modifie priorité/sévérité : c'est ta version “décisionnelle”.")

edited = st.data_editor(
    bl[[
        "irritant", "nb", "blocking", "neg_rate", "impact_score",
        "priorite_suggeree", "severite_suggeree",
        "priorite_finale", "severite_finale",
        "sample"
    ]],
    use_container_width=True,
    num_rows="fixed",
)

st.session_state["backlog_df_final"] = edited.copy()

st.divider()
st.download_button(
    "⬇️ Télécharger backlog CSV",
    data=edited.to_csv(index=False).encode("utf-8"),
    file_name="backlog.csv",
    mime="text/csv",
)
st.caption("Si tu vois encore ce bug, c’est un refresh Streamlit : le cache (data/_cache/topics_cache.csv) te sauve.")
