from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


# =========================
# Helpers
# =========================
def _safe_bool(x) -> bool:
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if x is None:
        return False
    s = str(x).strip().lower()
    return s in ("1", "true", "vrai", "yes", "y", "ok", "bloquant", "blocking")


def _safe_str(x) -> str:
    if x is None:
        return ""
    return str(x)


def _norm_theme(x: str) -> str:
    x = _safe_str(x).strip()
    return x if x else "Autre"


def _norm_sentiment(x: str) -> str:
    x = _safe_str(x).strip().lower()
    # formats acceptés
    if x in ("negatif", "négatif", "negative", "bad", "ko", "-1"):
        return "Négatif"
    if x in ("positif", "positive", "good", "ok", "1"):
        return "Positif"
    if x in ("neutre", "neutral", "0"):
        return "Neutre"
    return "Neutre"


def _clip01(v: float) -> float:
    return float(max(0.0, min(1.0, v)))


def _guess_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    cols = list(df.columns)
    low = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand in cols:
            return cand
        if cand.lower() in low:
            return low[cand.lower()]
    return None


# =========================
# Business scoring logic
# =========================
@dataclass
class ImpactWeights:
    """
    Impact business = combinaison de :
    - volume (nb)
    - blocage (part_blocking)
    - négatif (part_neg)
    """
    w_volume: float = 0.35
    w_blocking: float = 0.45
    w_neg: float = 0.20


def _impact_score(nb: int, part_blocking: float, part_neg: float, max_nb: int, w: ImpactWeights) -> float:
    # volume normalisé
    vol = 0.0 if max_nb <= 0 else (nb / max_nb)
    vol = _clip01(vol)
    return 100.0 * (
        w.w_volume * vol +
        w.w_blocking * _clip01(part_blocking) +
        w.w_neg * _clip01(part_neg)
    )


def _priority_from_rates(nb: int, part_blocking: float, part_neg: float) -> str:
    """
    Règles explicites et robustes (dataset orienté incidents).
    - P0 : blocage fort ET très fréquent
    - P1 : fréquent (utile en comité produit)
    - P2 : longue traîne / bruit
    """
    # P0 = blocage fort + volume significatif
    if part_blocking >= 0.30 and nb >= 300:
        return "P0"

    # P1 = suffisamment fréquent pour être actionnable (même si bloquant)
    if nb >= 100:
        return "P1"

    return "P2"


def _severity_from_rates(part_blocking: float, part_neg: float) -> str:
    # S1: très dur, S2: moyen, S3: faible
    if part_blocking >= 0.25 or part_neg >= 0.55:
        return "S1"
    if part_blocking >= 0.10 or part_neg >= 0.35:
        return "S2"
    return "S3"


def _recommendation(theme: str, priority: str, severity: str) -> str:
    # recommandation simple, orientée produit
    base = {
        "Connexion / Auth": "Réduire frictions login (messages d’erreur clairs, reset MDP, stabilité session).",
        "Performance / Lenteur": "Optimiser temps de réponse (lazy loading, cache, monitoring, budgets perf).",
        "Bug / Crash": "Stabiliser (logs, reproduction, correctifs hotfix, tests de non-régression).",
        "Export / Téléchargement": "Sécuriser export (file size, timeout, async job, reprise).",
        "Recherche / Navigation": "Clarifier IA/filtre/recherche + accessibilité des écrans clés.",
        "Paiement": "Fiabiliser étapes (3DS, erreurs, retry, confirmation, anti-double débit).",
        "Retour / Remboursement": "Rendre le statut transparent + parcours guidé + délais annoncés.",
        "Support": "Réduire escalades (selfcare, macros, SLA, routage).",
        "UX / Trop de clics": "Simplifier parcours (réduire étapes, auto-remplissage, actions groupées).",
    }.get(theme, "Analyser les exemples, créer une règle de routage (mots-clés) et proposer une action produit.")

    if priority == "P0":
        return "🚨 P0 : " + base
    if priority == "P1":
        return "⚠️ P1 : " + base
    return "✅ P2 : " + base


# =========================
# Public API required by app.py
# =========================
def theme_table(topics: pd.DataFrame) -> pd.DataFrame:
    """
    Agrège le dataframe topics (sortie NLP) en table thèmes :
    colonnes attendues: theme, nb, nb_blocking, part_blocking, part_neg, part_low_conf
    """
    if topics is None or len(topics) == 0:
        return pd.DataFrame(columns=["theme", "nb", "nb_blocking", "part_blocking", "part_neg", "part_low_conf"])

    t = topics.copy()

    theme_col = _guess_col(t, ["theme"])
    sent_col = _guess_col(t, ["sentiment"])
    block_col = _guess_col(t, ["blocking", "blocage"])
    lowc_col = _guess_col(t, ["low_confidence", "low_conf", "qc_faible", "confidence"])

    if theme_col is None:
        t["theme"] = "Autre"
        theme_col = "theme"

    if sent_col is None:
        t["sentiment"] = "Neutre"
        sent_col = "sentiment"

    if block_col is None:
        t["blocking"] = False
        block_col = "blocking"

    # normalise
    t["__theme"] = t[theme_col].map(_norm_theme)
    t["__sent"] = t[sent_col].map(_norm_sentiment)
    t["__block"] = t[block_col].map(_safe_bool)

    if lowc_col is not None:
        if pd.api.types.is_numeric_dtype(t[lowc_col]):
            t["__lowc"] = t[lowc_col].fillna(0).astype(float) < 0.5
        else:
            t["__lowc"] = t[lowc_col].map(_safe_bool)
    else:
        t["__lowc"] = False

    agg = t.groupby("__theme", dropna=False).agg(
        nb=("__theme", "size"),
        nb_blocking=("__block", "sum"),
        part_blocking=("__block", "mean"),
        part_neg=("__sent", lambda s: float((s == "Négatif").mean())),
        part_low_conf=("__lowc", "mean"),
    ).reset_index().rename(columns={"__theme": "theme"})

    agg = agg.sort_values(["nb", "nb_blocking", "part_neg"], ascending=False).reset_index(drop=True)
    return agg


def backlog_from_theme_table(tt: pd.DataFrame, weights: ImpactWeights | None = None) -> pd.DataFrame:
    """
    Transforme theme_table -> backlog décisionnel.
    Colonnes: irritant, nb, nb_blocking, part_blocking, part_neg, impact_score,
             priorite_finale, severite_finale, recommandation
    """
    weights = weights or ImpactWeights()

    if tt is None or len(tt) == 0:
        return pd.DataFrame(
            columns=[
                "irritant", "nb", "nb_blocking", "part_blocking", "part_neg",
                "impact_score", "priorite_finale", "severite_finale", "recommandation"
            ]
        )

    df = tt.copy()

    # sécurise colonnes
    for c in ["theme", "nb", "nb_blocking", "part_blocking", "part_neg"]:
        if c not in df.columns:
            df[c] = 0

    df["nb"] = df["nb"].fillna(0).astype(int)
    df["nb_blocking"] = df["nb_blocking"].fillna(0).astype(int)
    df["part_blocking"] = df["part_blocking"].fillna(0).astype(float)
    df["part_neg"] = df["part_neg"].fillna(0).astype(float)

    max_nb = int(df["nb"].max()) if len(df) else 0

    df["impact_score"] = df.apply(
        lambda r: _impact_score(
            int(r["nb"]),
            float(r["part_blocking"]),
            float(r["part_neg"]),
            max_nb=max_nb,
            w=weights
        ),
        axis=1,
    )

    df["priorite_finale"] = df.apply(
        lambda r: _priority_from_rates(
            int(r["nb"]),
            float(r["part_blocking"]),
            float(r["part_neg"]),
        ),
        axis=1,
    )

    df["severite_finale"] = df.apply(
        lambda r: _severity_from_rates(float(r["part_blocking"]), float(r["part_neg"])),
        axis=1,
    )

    df["recommandation"] = df.apply(
        lambda r: _recommendation(
            _safe_str(r["theme"]),
            _safe_str(r["priorite_finale"]),
            _safe_str(r["severite_finale"]),
        ),
        axis=1,
    )

    out = df.rename(columns={"theme": "irritant"})[
        ["irritant", "nb", "nb_blocking", "part_blocking", "part_neg",
         "impact_score", "priorite_finale", "severite_finale", "recommandation"]
    ].sort_values("impact_score", ascending=False).reset_index(drop=True)

    return out
