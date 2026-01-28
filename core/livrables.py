import sys
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="INSIGHTIA — Livrables", layout="wide")
st.title("4) Livrables")

topics = st.session_state.get("topics_df")
backlog = st.session_state.get("backlog_df_final")

if topics is None or backlog is None:
    st.warning("Va d’abord sur **2) Analyse** puis **3) Backlog**.")
    st.stop()

st.subheader("Exports")
c1, c2 = st.columns(2)

with c1:
    st.download_button(
        "⬇️ Télécharger commentaires_topics.csv",
        data=topics.to_csv(index=False).encode("utf-8"),
        file_name="commentaires_topics.csv",
        mime="text/csv",
    )

with c2:
    st.download_button(
        "⬇️ Télécharger backlog.csv",
        data=backlog.to_csv(index=False).encode("utf-8"),
        file_name="backlog.csv",
        mime="text/csv",
    )

st.divider()

st.subheader("Synthèse (Executive Summary)")
top = backlog.sort_values("impact_score", ascending=False).head(7)

lines = []
lines.append("## Points clés")
lines.append(f"- Verbatims analysés : **{len(topics)}**")
lines.append(f"- Thèmes uniques : **{topics['theme'].nunique()}**")
lines.append(f"- Blocages (P0 potentiels) : **{int(topics['blocking'].sum())}**")
lines.append("")
lines.append("## Top irritants (par impact)")
for _, r in top.iterrows():
    lines.append(f"- **{r['irritant']}** — nb={int(r['nb'])} — P={r['priorite_finale']} — Sev={r['severite_finale']}")

st.markdown("\n".join(lines))
