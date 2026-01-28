# decision_mapping.py
# Logique métier explicite (domain-agnostic)

def compute_is_negative(row) -> bool:
    """
    Décide si un verbatim est négatif (signal décisionnel).
    """
    s = str(row.get("sentiment_pred", "")).strip().lower()
    return s in ("négatif", "neg", "negative")


def compute_is_blocking(row) -> bool:
    """
    Décide si un verbatim est bloquant pour l'utilisateur.
    Règle volontairement stricte.
    """

    # 1) Incident explicite = bloquant
    if bool(row.get("incident", False)):
        return True

    # 2) Thèmes critiques + négatif
    theme = str(row.get("theme", "")).strip()

    THEMES_CRITIQUES = {
        "Paiement / Facturation / Abonnement",
        "Compte / Connexion / Authentification",
        "Technique / Bug / Fonctionnalité",
        "Performance / Lenteur",
    }

    if theme in THEMES_CRITIQUES:
        return compute_is_negative(row)

    return False


def compute_low_confidence(row) -> bool:
    """
    Décide si la classification est peu fiable.
    """
    theme = str(row.get("theme", "")).strip().lower()

    score = row.get("score_categorie", 1.0)
    try:
        score = float(score)
    except Exception:
        score = 1.0

    return (
        score < 0.6
        or bool(row.get("contradiction", False))
        or theme in ("autre", "inconnu")
    )
