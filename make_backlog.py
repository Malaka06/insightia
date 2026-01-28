from __future__ import annotations

from pathlib import Path
import pandas as pd

from insightia.core.scoring import theme_table, backlog_from_theme_table, ImpactWeights


def generate_backlog_from_topics(
    topics_df: pd.DataFrame,
    domain: str = "assurance_auto",
    p1_min_nb: int = 100,
) -> pd.DataFrame:
    """
    Génère un backlog priorisé à partir du DataFrame topics.

    - Normalise les colonnes attendues (robuste si manquantes)
    - Neutralise Autre/Inconnu AVANT scoring
    - Applique règle P1 par volume (nb >= p1_min_nb) pour tout ce qui n'est pas P0
    - Règle absolue finale : Autre/Inconnu => P2 + S3
    - Recalcule le préfixe de recommandation selon priorite_finale
    """
    df = topics_df.copy()

    # Sécurités si colonnes manquent (compat avec scoring / historiques)
    for col in ["sentiment_pred", "incident", "score_categorie", "contradiction", "theme", "text_norm"]:
        if col not in df.columns:
            df[col] = None

    # 1) Sentiment décisionnel (mapping)
    df["sentiment"] = df["sentiment_pred"].map(
        {"Négatif": "Négatif", "Neutre": "Neutre", "Positif": "Positif"}
    ).fillna("Neutre")

    # 2) Blocking = incident uniquement (base saine)
    df["blocking"] = df["incident"].fillna(False).astype(bool)

    # 3) Low confidence
    df["low_confidence"] = (
        (pd.to_numeric(df["score_categorie"], errors="coerce").fillna(1.0) < 0.6)
        | (df["contradiction"].fillna(False).astype(bool))
        | (df["theme"].astype(str).str.strip().str.lower().isin(["autre", "inconnu"]))
    )

    # 4) Neutralisation AVANT scoring (critique)
    mask_residu_df = df["theme"].astype(str).str.strip().str.lower().isin(["autre", "inconnu"])
    df.loc[mask_residu_df, "blocking"] = False
    df.loc[mask_residu_df, "sentiment"] = "Neutre"

    # 5) Scoring -> backlog
    tt = theme_table(df)
    weights = ImpactWeights(w_volume=0.40, w_blocking=0.35, w_neg=0.25)
    backlog = backlog_from_theme_table(tt, weights=weights)

    # 6) Règle P1 par volume (nb >= p1_min_nb) pour tout ce qui n'est pas P0
    mask_not_p0 = backlog["priorite_finale"] != "P0"
    backlog.loc[mask_not_p0 & (backlog["nb"] >= int(p1_min_nb)), "priorite_finale"] = "P1"
    backlog.loc[mask_not_p0 & (backlog["nb"] < int(p1_min_nb)), "priorite_finale"] = "P2"

    # 7) RÈGLE ABSOLUE FINALE (toujours en dernier)
    mask_residu_final = backlog["irritant"].astype(str).str.strip().str.lower().isin(["autre", "inconnu"])
    backlog.loc[mask_residu_final, "priorite_finale"] = "P2"
    backlog.loc[mask_residu_final, "severite_finale"] = "S3"

    # 8) Recalcul du préfixe recommandation (cohérent avec priorite_finale)
    def _prefix(prio: str) -> str:
        return "🚨 P0 : " if prio == "P0" else ("⚠️ P1 : " if prio == "P1" else "✅ P2 : ")

    if "recommandation" in backlog.columns:
        backlog["recommandation"] = backlog.apply(
            lambda r: _prefix(str(r["priorite_finale"])) + str(r["recommandation"]).split(":", 1)[-1].strip(),
            axis=1,
        )

    return backlog


# ============================================================
# MODE SCRIPT (optionnel) : CSV topics -> backlog.csv
# Protégé pour ne PAS s’exécuter quand Streamlit importe le module
# ============================================================
if __name__ == "__main__":
    TOPICS_PATH = Path("insightia/data/commentaires_topics.csv")
    OUT_BACKLOG = Path("insightia/data/backlog.csv")

    if not TOPICS_PATH.exists():
        raise FileNotFoundError(f"Fichier introuvable: {TOPICS_PATH}")

    df = pd.read_csv(TOPICS_PATH)

    backlog = generate_backlog_from_topics(
        topics_df=df,
        domain="assurance_auto",
        p1_min_nb=100,
    )

    OUT_BACKLOG.parent.mkdir(parents=True, exist_ok=True)
    backlog.to_csv(OUT_BACKLOG, index=False, encoding="utf-8")

    print("\n✅ backlog.csv généré :", OUT_BACKLOG)
    print("\n🔝 TOP 10 BACKLOG :")
    print(backlog.head(10))
