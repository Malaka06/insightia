# taxonomy.py
# Gestion des taxonomies par domaine

from typing import Optional
import pandas as pd

DEFAULT_THEMES = [
    "Technique / Bug / Fonctionnalité",
    "Performance / Lenteur",
    "Compte / Connexion / Authentification",
    "Paiement / Facturation / Abonnement",
    "Support / Service client",
    "UX / Parcours",
    "Contrat / Documents",
    "Sinistre / Indemnisation",
    "Autre",
    "Inconnu",
]

DOMAIN_TAXONOMIES = {
    "assurance_auto": [
        "Sinistre / Collision / Accident",
        "Sinistre / Bris de glace",
        "Sinistre / Catastrophe naturelle",
        "Déclaration / Justificatifs / Parcours",
        "Contrat / Garanties / Profil assuré",
        "Compte / Connexion / Authentification",
        "Paiement / Facturation / Abonnement",
        "Autre",
        "Inconnu",
    ],
    "ecommerce": [
        "Commande / Paiement",
        "Livraison",
        "Retour / Remboursement",
        "Produit / Qualité",
        "Compte / Connexion",
        "Support client",
        "Autre",
        "Inconnu",
    ],
    "saas": [
        "Connexion / Authentification",
        "Bug / Crash",
        "Performance",
        "Facturation",
        "Données / Perte",
        "UX / Complexité",
        "Autre",
        "Inconnu",
    ],
}

TEXT_CANDIDATES = [
    "texte", "text",
    "commentaire", "commentaires",
    "verbatim", "verbatims",
    "message", "messages",
    "feedback", "feedbacks",
    "review", "reviews",
    "avis",
    "description",
]


def get_taxonomy(domain: Optional[str] = None):
    """Retourne la taxonomie associée à un domaine."""
    if domain and domain in DOMAIN_TAXONOMIES:
        return DOMAIN_TAXONOMIES[domain]
    return DEFAULT_THEMES


def ensure_text(df: pd.DataFrame, preferred: Optional[str] = None) -> pd.DataFrame:
    """
    Garantit une colonne canonique 'texte' pour le pipeline.

    Règles (défendables) :
    - Si 'texte' existe déjà : nettoyage léger (NaN -> "", strip).
    - Sinon : on cherche une colonne probable (candidats connus + fallback 1ère colonne object).
    - Si aucune colonne exploitable : on crée 'texte' vide (pas d'invention).
    """
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError("ensure_text attend un DataFrame pandas.")

    out = df.copy()

    # 1) Déjà présent
    if "texte" in out.columns:
        out["texte"] = out["texte"].fillna("").astype(str).map(lambda x: x.strip())
        return out

    # 2) Colonne préférée
    if preferred and preferred in out.columns:
        src = preferred
    else:
        # 3) Candidats connus (case-insensitive)
        src = None
        lower_map = {c.lower(): c for c in out.columns}
        for cand in TEXT_CANDIDATES:
            if cand in lower_map:
                src = lower_map[cand]
                break

        # 4) Fallback : première colonne textuelle
        if src is None:
            obj_cols = [c for c in out.columns if out[c].dtype == "object"]
            src = obj_cols[0] if obj_cols else None

    # 5) Canonisation
    if src is None:
        out["texte"] = ""
        return out

    out["texte"] = out[src].fillna("").astype(str).map(lambda x: x.strip())
    return out
