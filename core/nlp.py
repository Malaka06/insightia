from __future__ import annotations

import re
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd


# -------------------------
# Normalisation
# -------------------------
_RE_SPACES = re.compile(r"\s+")
_RE_PUNCT = re.compile(r"[^\w\sÀ-ÿ'-]+")

def normalize_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = _RE_PUNCT.sub(" ", s)
    s = _RE_SPACES.sub(" ", s).strip()
    return s


# -------------------------
# Sentiment (simple & explicable)
# -------------------------
NEG = {
    "impossible", "bloque", "bloquant", "bug", "crash", "erreur",
    "ne marche pas", "marche pas", "ne fonctionne pas", "fonctionne pas",
    "lent", "lenteur", "interminable", "timeout", "refusé", "refuse", "échec", "echec",
    "inadmissible", "horrible", "nul", "déçu", "decu", "problème", "probleme",
}
POS = {"merci", "parfait", "super", "excellent", "top", "rapide", "simple", "efficace", "satisfait", "content"}

def sentiment(text_norm: str) -> tuple[str, float]:
    if not text_norm:
        return "Neutre", 0.0
    n = sum(1 for w in NEG if w in text_norm)
    p = sum(1 for w in POS if w in text_norm)
    score = (p - n) / max(1, p + n)
    if score <= -0.25:
        return "Négatif", float(score)
    if score >= 0.25:
        return "Positif", float(score)
    return "Neutre", float(score)


# -------------------------
# Blocage (parcours clé)
# -------------------------
BLOCK_PATTERNS = [
    r"\bimpossible\b",
    r"\bbloqu(e|é|ant)\b|\bça bloque\b",
    r"\bne marche pas\b|\bmarche pas\b",
    r"\bne fonctionne pas\b|\bfonctionne pas\b",
    r"\berreur\s*([0-9]{3,4})\b",
    r"\bcrash\b",
    r"\btimeout\b",
    r"\bchargement (infini|interminable)\b|\bpage (qui )?tourne\b",
]

def is_blocking(text_norm: str) -> bool:
    if not text_norm:
        return False
    return any(re.search(p, text_norm) for p in BLOCK_PATTERNS)

def blocking_reason(text_norm: str) -> str:
    if not text_norm:
        return "Inconnu"
    m = re.search(r"erreur\s*([0-9]{3,4})", text_norm)
    if m:
        return f"Erreur {m.group(1)}"
    if "crash" in text_norm:
        return "Crash"
    if "timeout" in text_norm:
        return "Timeout"
    if "chargement" in text_norm or "tourne" in text_norm:
        return "Chargement infini"
    if "impossible" in text_norm:
        return "Action impossible"
    if "bloque" in text_norm:
        return "Blocage parcours"
    return "Blocage"


# -------------------------
# Thèmes universels + sectoriels (sans topic modeling)
# -------------------------
DEFAULT_THEMES: Dict[str, List[str]] = {
    "Connexion / Auth": ["connexion", "login", "mot de passe", "mdp", "auth", "2fa", "otp", "code", "session", "sso"],
    "Bug / Crash": ["bug", "crash", "erreur", "exception", "500", "404", "plante", "freeze", "ko"],
    "Performance / Lenteur": ["lent", "lenteur", "long", "interminable", "latence", "lag", "chargement"],
    "Export / Téléchargement": ["export", "télécharger", "telecharger", "csv", "pdf", "excel", "download", "rapport"],
    "UX / Parcours": ["compliqué", "complexe", "trop de clics", "trop d'étapes", "ergonomie", "interface"],
    "Support": ["support", "sav", "service client", "ticket", "conseiller", "chat", "email", "mail", "téléphone", "appel"],

    "Commande": ["commande", "panier", "checkout", "valider", "annuler", "confirmation"],
    "Paiement": ["paiement", "payer", "carte", "cb", "stripe", "paypal", "refusé", "refuse", "échec", "echec", "facture"],
    "Livraison": ["livraison", "colis", "transporteur", "suivi", "retard", "expedition", "reception", "réception", "ups", "dpd", "chronopost", "mondial"],
    "Retour / Remboursement": ["retour", "remboursement", "rembourser", "avoir"],

    "Satisfaction": ["merci", "super", "excellent", "parfait", "top", "rapide", "simple", "efficace", "satisfait", "content"],
}

DEFAULT_JOURNEYS: Dict[str, List[str]] = {
    "Onboarding": ["inscription", "créer un compte", "creer un compte", "activation", "première connexion", "premiere connexion"],
    "Connexion": ["connexion", "login", "auth", "mot de passe", "2fa", "otp", "sso"],
    "Parcours clé": ["payer", "valider", "finaliser", "soumettre", "sauvegarder", "enregistrer", "export"],
    "Support": ["support", "ticket", "sav", "conseiller", "chat", "appel", "email", "mail"],
}

def _keyword_score(text_norm: str, keywords: List[str]) -> int:
    score = 0
    for kw in keywords:
        if kw and kw in text_norm:
            score += 1
    return score

def classify_theme(
    text_norm: str,
    user_themes: Optional[Dict[str, List[str]]] = None
) -> tuple[str, float, str]:
    themes = dict(DEFAULT_THEMES)
    if user_themes:
        themes.update(user_themes)

    if not text_norm:
        return "Autre", 0.0, "empty"

    scored = []
    for theme, kws in themes.items():
        s = _keyword_score(text_norm, [k.lower() for k in kws])

        # bonus léger si blocage et thème technique
        if is_blocking(text_norm) and theme in {"Connexion / Auth", "Bug / Crash", "Performance / Lenteur", "Paiement"}:
            s += 1

        if s > 0:
            scored.append((theme, s))

    if not scored:
        # fallback intelligent: si blocage => pas “Autre”
        if is_blocking(text_norm):
            return "Bug / Crash", 0.40, "blocking_fallback"
        return "Autre", 0.18, "no_match"

    scored.sort(key=lambda x: x[1], reverse=True)
    top_theme, top = scored[0]
    second = scored[1][1] if len(scored) > 1 else 0

    conf = (top - second) / max(1, top)
    conf = float(np.clip(conf, 0.0, 1.0))
    if top >= 3:
        conf = max(conf, 0.65)

    return top_theme, conf, "keyword_scoring"

def detect_journey(
    text_norm: str,
    user_journeys: Optional[Dict[str, List[str]]] = None
) -> tuple[str, float]:
    journeys = dict(DEFAULT_JOURNEYS)
    if user_journeys:
        journeys.update(user_journeys)

    if not text_norm:
        return "Autre", 0.0

    best_j, best_s = "Autre", 0
    for j, kws in journeys.items():
        s = _keyword_score(text_norm, [k.lower() for k in kws])
        if s > best_s:
            best_s = s
            best_j = j

    if best_j == "Autre" and is_blocking(text_norm):
        return "Parcours clé", 0.10

    conf = float(best_s / max(3, len(journeys.get(best_j, [])) or 3))
    return best_j, conf


# -------------------------
# ✅ EXPORT PRINCIPAL ATTENDU PAR APP.PY
# -------------------------
def run_pipeline(
    df: pd.DataFrame,
    user_themes: Optional[Dict[str, List[str]]] = None,
    user_journeys: Optional[Dict[str, List[str]]] = None,
) -> pd.DataFrame:
    """
    Pipeline léger (explicable) :
    - nécessite df['texte']
    - produit : text_norm, sentiment, blocking, theme, confidence, journey...
    """
    out = df.copy()
    if "texte" not in out.columns:
        raise ValueError("La colonne 'texte' est obligatoire (utilise ensure_text avant run_pipeline).")

    out["text_norm"] = out["texte"].astype(str).fillna("").map(normalize_text)

    s = out["text_norm"].map(sentiment)
    out["sentiment"] = s.map(lambda x: x[0])
    out["score_sentiment"] = s.map(lambda x: x[1])

    out["blocking"] = out["text_norm"].map(is_blocking)
    out["blocking_reason"] = out["text_norm"].map(blocking_reason)

    j = out["text_norm"].map(lambda t: detect_journey(t, user_journeys))
    out["journey"] = j.map(lambda x: x[0])
    out["journey_conf"] = j.map(lambda x: x[1])

    th = out["text_norm"].map(lambda t: classify_theme(t, user_themes))
    out["theme"] = th.map(lambda x: x[0])
    out["confidence"] = th.map(lambda x: x[1])
    out["methode_categorie"] = th.map(lambda x: x[2])

    out["low_confidence"] = out["confidence"] < 0.35
    return out
