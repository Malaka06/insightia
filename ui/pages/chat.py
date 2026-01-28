from __future__ import annotations

import streamlit as st
import pandas as pd

from dataclasses import dataclass
from typing import List, Optional

from core.reporting import build_executive_summary


# ============================================================
# Modèle de réponse structurée
# ============================================================

@dataclass(frozen=True)
class AssistantResponse:
    title: str
    constat: List[str]
    risque: List[str]
    actions: List[str]

    def to_markdown(self) -> str:
        lines: List[str] = []
        lines.append(f"**{self.title}**")
        lines.append("")
        lines.append("**Constat**")
        for c in self.constat:
            lines.append(f"- {c}")
        lines.append("")
        lines.append("**Risque business**")
        for r in self.risque:
            lines.append(f"- {r}")
        lines.append("")
        lines.append("**Actions recommandées**")
        for a in self.actions:
            lines.append(f"- {a}")
        return "\n".join(lines)


def _pct(x: float) -> str:
    try:
        return f"{float(x) * 100:.0f}%"
    except Exception:
        return "0%"


def _safe_df(df) -> bool:
    return df is not None and isinstance(df, pd.DataFrame) and not df.empty


def _kpi(topics: pd.DataFrame) -> dict:
    nb = float(len(topics)) if _safe_df(topics) else 0.0

    autre = (
        float((topics["theme"].astype(str) == "Autre").mean())
        if _safe_df(topics) and "theme" in topics.columns
        else 0.0
    )
    coverage = 1.0 - autre if nb else 0.0

    neg = (
        float((topics["sentiment"].astype(str) == "Négatif").mean())
        if _safe_df(topics) and "sentiment" in topics.columns
        else 0.0
    )

    blk = (
        float(pd.to_numeric(topics["blocking"], errors="coerce").fillna(0).mean())
        if _safe_df(topics) and "blocking" in topics.columns
        else 0.0
    )

    return {"nb": nb, "autre": autre, "coverage": coverage, "neg": neg, "blk": blk}


def _top_backlog(backlog: Optional[pd.DataFrame], n: int = 5) -> pd.DataFrame:
    if not _safe_df(backlog):
        return pd.DataFrame()
    if "impact_score" in backlog.columns:
        return backlog.sort_values("impact_score", ascending=False).head(n).copy()
    if "nb" in backlog.columns:
        return backlog.sort_values("nb", ascending=False).head(n).copy()
    return backlog.head(n).copy()


def assistant_suggestions(
    topics: Optional[pd.DataFrame],
    backlog: Optional[pd.DataFrame],
) -> List[str]:
    if not _safe_df(topics):
        return [
            "Importer un CSV puis lancer l’analyse",
            "Tester une démo (SaaS / E-commerce)",
        ]

    k = _kpi(topics)
    s: List[str] = []

    if k["autre"] >= 0.2:
        s.append("Pourquoi “Autre” est élevé, et comment le réduire ?")
    if _safe_df(backlog):
        s.append("Quelles sont les top priorités (P0/P1) et pourquoi ?")
    if k["blk"] >= 0.05:
        s.append("Quels sont les principaux blocages parcours ?")
    if k["neg"] >= 0.25:
        s.append("Quels irritants concentrent l’insatisfaction ?")
    if not s:
        s.append("Quelle est la synthèse exécutive de cette analyse ?")

    return s[:5]


def assistant_answer(
    question: str,
    topics: Optional[pd.DataFrame] = None,
    backlog: Optional[pd.DataFrame] = None,
) -> str:
    """
    Assistant InsightIA — local, sans API.
    Sortie structurée : Constat → Risque business → Actions recommandées.
    """
    q = (question or "").strip()
    ql = q.lower()

    if not _safe_df(topics):
        return AssistantResponse(
            title="Assistant InsightIA",
            constat=["Aucune donnée analysée n’est disponible."],
            risque=["Impossible d’identifier des priorités sans résultats."],
            actions=["Importer un CSV ou tester une démo, puis lancer l’analyse."],
        ).to_markdown()

    k = _kpi(topics)

    # Question vide → snapshot + suggestions
    if not q:
        sugg = assistant_suggestions(topics, backlog)
        return AssistantResponse(
            title="Assistant InsightIA",
            constat=[
                f"Volume analysé : {int(k['nb'])} verbatims.",
                f"Couverture hors “Autre” : {_pct(k['coverage'])}.",
                f"Insatisfaction : {_pct(k['neg'])}.",
                f"Blocages : {_pct(k['blk'])}.",
            ],
            risque=["Sans arbitrage clair, les efforts produit et opérations peuvent se disperser."],
            actions=[f"Suggestion : {s}" for s in sugg],
        ).to_markdown()

    # Rapport / synthèse
    if any(x in ql for x in ["synthèse", "rapport", "résumé", "executive"]):
        return build_executive_summary(topics, backlog).to_markdown()

    # Priorisation
    if any(x in ql for x in ["priorité", "p0", "p1", "top", "impact", "prioriser"]):
        top = _top_backlog(backlog, n=5)
        if top.empty:
            return AssistantResponse(
                title="Priorisation",
                constat=["Le backlog n’est pas disponible ou incomplet."],
                risque=["La priorisation est fragile sans score d’impact."],
                actions=["Aller sur la page Priorisation pour générer le backlog puis revenir ici."],
            ).to_markdown()

        lines = []
        for _, r in top.iterrows():
            irr = str(r.get("irritant", ""))
            p = str(r.get("priorite_finale", "P1"))
            s = str(r.get("severite_finale", "S2"))
            imp = r.get("impact_score", None)
            imp_txt = f"{float(imp):.1f}" if imp is not None and pd.notna(imp) else "—"
            lines.append(f"{irr} — {p}/{s} — impact {imp_txt}")

        return AssistantResponse(
            title="Top priorités",
            constat=lines,
            risque=["Les sujets P0 non traités peuvent impacter conversion et satisfaction."],
            actions=[
                "Traiter le premier P0 immédiatement.",
                "Valider la cause racine sur 10–20 verbatims.",
                "Planifier les P1 avec critères de succès mesurables.",
            ],
        ).to_markdown()

    # Autre
    if "autre" in ql:
        return AssistantResponse(
            title="Réduction de “Autre”",
            constat=[f"Part “Autre” : {_pct(k['autre'])}."],
            risque=["Un “Autre” élevé masque des irritants actionnables."],
            actions=[
                "Inspecter 20 verbatims “Autre”.",
                "Créer 2–4 sous-thèmes stables.",
                "Relancer l’analyse.",
            ],
        ).to_markdown()

    # Fallback
    return AssistantResponse(
        title="Assistant InsightIA",
        constat=["Question trop générale pour produire une décision claire."],
        risque=["Une réponse floue peut conduire à de mauvaises priorités."],
        actions=[
            "Pose une question orientée décision.",
            "Exemples : « top priorités », « synthèse », « pourquoi Autre ? »",
        ],
    ).to_markdown()


# ============================================================
# UI Chat (Streamlit)
# ============================================================

def render():
    st.title("Chat Insightia")
    st.caption("Assistant local (sans API). Basé sur tes résultats d’analyse et ton backlog.")

    # Récupération des données (si disponibles)
    topics = st.session_state.get("ana_nlp_df")
    backlog = st.session_state.get("backlog_df")

    # Initialiser historique
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": assistant_answer("", topics=topics, backlog=backlog)}
        ]

    # Boutons utilitaires
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("🧹 Réinitialiser", use_container_width=True):
            st.session_state.chat_messages = [
                {"role": "assistant", "content": assistant_answer("", topics=topics, backlog=backlog)}
            ]
            st.rerun()
    with c2:
        if st.button("📊 Aller à l'analyse", use_container_width=True):
            st.query_params["page"] = "analysis"
            st.rerun()
    with c3:
        if st.button("🧩 Aller à la priorisation", use_container_width=True):
            st.query_params["page"] = "prioritization"
            st.rerun()

    # Affichage messages
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    prompt = st.chat_input("Écris une question (ex: “top priorités”, “synthèse exécutive”, “pourquoi Autre ?”)")

    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        answer = assistant_answer(prompt, topics=topics, backlog=backlog)
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
