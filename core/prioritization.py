# prioritization.py
# Fallback simple — PAS le moteur principal

def quick_priority_hint(text: str) -> str:
    """
    Donne un hint de priorité à partir du texte.
    Utilisé uniquement si le scoring principal est indisponible.
    """
    t = str(text).lower()

    if any(w in t for w in ["impossible", "bloqué", "crash", "erreur critique", "paiement refusé"]):
        return "P0"

    if any(w in t for w in ["lent", "bug", "problème", "difficile"]):
        return "P1"

    return "P2"
