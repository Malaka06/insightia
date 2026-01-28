# core/reporting.py
from __future__ import annotations

import pandas as pd


def build_executive_summary(
    topics: pd.DataFrame,
    backlog: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Génère une synthèse exécutive à partir :
    - des résultats NLP (topics)
    - du backlog priorisé (optionnel)

    Retourne un DataFrame prêt à afficher / exporter.
    """

    rows = []

    # -----------------------------
    # Analyse NLP (topics)
    # -----------------------------
    n_total = len(topics)

    if "sentiment" in topics.columns:
        neg_rate = (topics["sentiment"].astype(str) == "Négatif").mean()
    else:
        neg_rate = 0.0

    if "blocking" in topics.columns:
        try:
            block_rate = (
                pd.to_numeric(topics["blocking"], errors="coerce")
                .fillna(0)
                .mean()
            )
        except Exception:
            block_rate = topics["blocking"].fillna(False).astype(bool).mean()
    else:
        block_rate = 0.0

    n_themes = topics["theme"].nunique() if "theme" in topics.columns else 0

    rows.append(
        {
            "Section": "Analyse",
            "Indicateur": "Volume analysé",
            "Valeur": f"{n_total} verbatims",
            "Insight": "Base statistique suffisante pour une lecture fiable."
            if n_total >= 100
            else "Volume faible : interprétation prudente.",
        }
    )

    rows.append(
        {
            "Section": "Analyse",
            "Indicateur": "Taux de négatif",
            "Valeur": f"{neg_rate:.0%}",
            "Insight": "Insatisfaction significative."
            if neg_rate > 0.25
            else "Niveau d’insatisfaction contenu.",
        }
    )

    rows.append(
        {
            "Section": "Analyse",
            "Indicateur": "Taux bloquant",
            "Valeur": f"{block_rate:.0%}",
            "Insight": "Points bloquants à traiter en priorité."
            if block_rate > 0.10
            else "Peu de blocages critiques détectés.",
        }
    )

    rows.append(
        {
            "Section": "Analyse",
            "Indicateur": "Thèmes identifiés",
            "Valeur": str(n_themes),
            "Insight": "Couverture thématique satisfaisante."
            if n_themes >= 5
            else "Taxonomie à enrichir.",
        }
    )

    # -----------------------------
    # Backlog (actions)
    # -----------------------------
    if backlog is not None and not backlog.empty:
        if "priorite_finale" in backlog.columns:
            p0 = (backlog["priorite_finale"] == "P0").sum()
            p1 = (backlog["priorite_finale"] == "P1").sum()
        else:
            p0 = p1 = 0

        rows.append(
            {
                "Section": "Plan d’action",
                "Indicateur": "Actions critiques (P0)",
                "Valeur": str(p0),
                "Insight": "Actions immédiates recommandées."
                if p0 > 0
                else "Aucune action critique identifiée.",
            }
        )

        rows.append(
            {
                "Section": "Plan d’action",
                "Indicateur": "Actions importantes (P1)",
                "Valeur": str(p1),
                "Insight": "Quick wins ou actions court terme.",
            }
        )

    # -----------------------------
    # Conclusion
    # -----------------------------
    rows.append(
        {
            "Section": "Conclusion",
            "Indicateur": "Lecture globale",
            "Valeur": "—",
            "Insight": (
                "Les irritants principaux sont clairement identifiés et priorisés. "
                "La mise en œuvre du backlog permettra une réduction mesurable de l’insatisfaction."
            ),
        }
    )

    return pd.DataFrame(rows)
