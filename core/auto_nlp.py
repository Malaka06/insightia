from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple, Set

import pandas as pd
import streamlit as st


# =========================================================
# 1) STOPWORDS (FR + verbes fréquents + temps + bruit)
# =========================================================
STOPWORDS_FR: Set[str] = {
    # articles / pronoms / prépositions (base)
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "et", "ou", "à", "a",
    "en", "pour", "par", "sur", "avec", "sans", "ce", "ces", "cette", "cet",
    "se", "sa", "son", "ses", "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
    "mon", "ma", "mes", "ton", "ta", "tes", "leur", "leurs", "y", "en",

    # formes fréquentes
    "c", "ça", "ca", "cest", "c'est", "jai", "j'ai", "jsuis", "j", "t", "m",
    "qu", "que", "qui", "quoi", "dont",
    "oui", "non", "ok", "svp", "stp", "merci", "bonjour", "bonsoir",

    # verbes très fréquents (bruit)
    "est", "sont", "été", "etre", "être", "ai", "as", "avons", "avez", "ont",
    "vais", "va", "allons", "allez", "vont",
    "fait", "fais", "faites", "faire",
    "peux", "peut", "pouvez", "pouvoir",
    "dois", "doit", "devez", "devoir",
    "veux", "veut", "voulez", "vouloir",
    "viens", "vient", "venir",
    "met", "mets", "mettez", "mettre", "mis", "mise",
    "passe", "passer", "passé", "passée",
    "marche", "marcher", "fonctionne", "fonctionner",

    # temps / fréquence (bruit)
    "jour", "jours", "semaine", "semaines", "mois", "an", "ans", "heure", "heures",
    "minute", "minutes", "depuis", "avant", "apres", "après",
    "maintenant", "encore", "déjà", "toujours", "souvent",
    "rapidement", "lentement", "bientôt", "hier", "aujourd'hui", "demain",

    # mots vagues / peu discriminants
    "simple", "facile", "compliqué", "complexe", "problème", "probleme", "souci",
    "cas", "chose", "truc", "niveau", "genre", "style", "vraiment",
    "très", "tres", "super", "top", "nul", "bien", "mal",

    # connecteurs / remplissage
    "car", "donc", "alors", "mais", "puis", "ensuite", "comme", "quand", "lorsque", "aussi",
}


# =========================================================
# 2) STOPWORDS DYNAMIQUES (ajoutables sans recoder)
# =========================================================
DYNAMIC_STOPWORDS: Set[str] = set()


def add_dynamic_stopwords(words: List[str]) -> None:
    """
    Add stopwords at runtime (for calibration).
    Example: add_dynamic_stopwords(["client", "application"])
    """
    for w in words:
        w = str(w).strip().lower()
        if w:
            DYNAMIC_STOPWORDS.add(w)


# =========================================================
# 3) THEMES: mapping mots-clés → thème (par domaine)
# =========================================================
KEYWORDS_BY_DOMAIN: Dict[str, Dict[str, List[str]]] = {
    "default": {
        "Technique / Bug / Fonctionnalité": [
            "bug", "bogue", "crash", "plante", "plantage", "freeze", "bloque", "bloqué", "erreur",
            "message d'erreur", "code erreur", "inaccessible", "ne marche pas", "ne fonctionne pas",
            "fonctionne pas", "impossible", "impossible de", "ko", "hs", "maintenance",
            "mise à jour", "maj", "update", "fonction", "fonctionnalité", "option", "feature",
            "bouton", "lien", "page", "écran", "affichage", "chargement infini", "loading",
            "connexion au serveur", "serveur", "incident", "panne",
        ],
        "Performance / Lenteur": [
            "lent", "lenteur", "rame", "lag", "latence", "timeout", "temps de chargement",
            "trop long", "met du temps", "long à charger", "chargement", "ralenti",
            "ça rame", "ça lag", "bloqué sur chargement",
        ],
        "Compte / Connexion / Authentification": [
            "connexion", "connecter", "login", "log in", "identifiant", "mot de passe", "mdp",
            "reset", "réinitialiser", "réinitialisation", "mot de passe oublié",
            "auth", "authentification", "2fa", "double authentification", "sms", "code sms",
            "compte", "profil", "inscription", "s'inscrire", "créer un compte",
            "déconnexion", "session", "token", "accès refusé", "verrouillé", "bloqué", "sso",
        ],
        "Paiement / Facturation / Abonnement": [
            "paiement", "payer", "carte", "cb", "visa", "mastercard", "prélèvement", "prélevé",
            "virement", "iban", "facture", "facturation", "abonnement", "résiliation", "resilier",
            "annuler", "tarif", "prix", "trop cher", "promotion", "réduction", "remise",
            "double facturation", "facturé deux fois", "paiement refusé", "transaction",
            "chargeback", "remboursement",
        ],
        "Support / Service client": [
            "support", "service client", "sav", "assistance", "aide", "help", "ticket",
            "réponse", "aucune réponse", "pas de réponse", "injoignable", "joindre",
            "appel", "téléphone", "mail", "email", "chat", "conseiller", "agent",
            "attente", "trop d'attente", "relance", "rappel", "pas rappelé",
            "pas de suivi", "suivi", "délais de réponse",
        ],
        "UX / Parcours": [
            "ux", "ergonomie", "interface", "parcours", "navigation", "menu", "compliqué",
            "complexe", "pas clair", "incompréhensible", "confus", "difficile",
            "trop de clics", "je trouve pas", "je ne trouve pas", "introuvable",
            "workflow", "étapes", "formulaire", "champ", "validation", "design",
            "responsive", "mobile", "desktop",
        ],
        "Autre": [],
        "Inconnu": [],
    },

    "saas": {
        "Connexion / Authentification": [
            "connexion", "login", "identifiant", "mot de passe", "mdp", "sso", "oauth",
            "authentification", "2fa", "code", "sms", "token", "session expirée",
            "accès refusé", "permission", "droits", "rôle", "role", "compte verrouillé",
        ],
        "Bug / Crash": [
            "bug", "crash", "plante", "plantage", "freeze", "bloque", "erreur",
            "inaccessible", "incident", "panne", "ne marche pas", "ne fonctionne pas",
            "page blanche", "chargement infini",
        ],
        "Performance": [
            "lent", "lenteur", "lag", "latence", "timeout", "rame", "ralenti",
            "trop long", "met du temps", "chargement", "performance",
        ],
        "Facturation": [
            "facture", "facturation", "abonnement", "billing", "paiement", "prélèvement",
            "prélevé", "tarif", "prix", "plan", "upgrade", "downgrade",
            "résiliation", "annuler", "renouvellement", "double facturation",
            "paiement refusé", "carte expirée",
        ],
        "Données / Perte": [
            "donnée", "données", "data", "perte", "perdu", "supprimé", "effacé",
            "export", "import", "synchronisation", "sync", "backup", "sauvegarde",
            "restaurer", "historique", "logs", "audit", "reporting",
        ],
        "UX / Complexité": [
            "ux", "interface", "ergonomie", "parcours", "workflow", "compliqué",
            "complexe", "pas clair", "incompréhensible", "navigation", "menu",
            "paramètres", "configuration", "onboarding",
        ],
        "Autre": [],
        "Inconnu": [],
    },

    "ecommerce": {
        "Commande / Paiement": [
            "commande", "commander", "panier", "checkout", "paiement", "payer", "cb", "carte",
            "transaction", "paiement refusé", "erreur de paiement", "validation",
            "code promo", "coupon", "promotion", "réduction", "remise",
            "facture", "facturation",
        ],
        "Livraison": [
            "livraison", "livrer", "colis", "transporteur", "suivi", "tracking",
            "retard", "en retard", "pas reçu", "jamais reçu", "livré", "point relais",
            "relais", "adresse", "colis perdu", "frais de livraison",
        ],
        "Retour / Remboursement": [
            "retour", "renvoi", "remboursement", "rembourser", "rétractation",
            "étiquette", "retourner", "annulation", "annuler", "avoir", "bon d'achat",
        ],
        "Produit / Qualité": [
            "produit", "qualité", "cassé", "défectueux", "abîmé", "non conforme",
            "taille", "trop petit", "trop grand", "couleur", "description",
        ],
        "Compte / Connexion": [
            "compte", "connexion", "login", "mot de passe", "inscription", "créer un compte",
            "email", "adresse email",
        ],
        "Support client": [
            "support", "service client", "sav", "réponse", "pas de réponse",
            "chat", "email", "téléphone", "appel", "ticket", "litige",
        ],
        "Autre": [],
        "Inconnu": [],
    },

    "assurance_auto": {
        "Sinistre / Accident": [
            "sinistre", "accident", "collision", "choc", "accrochage", "responsable",
            "constat", "constat amiable", "déclaration", "dossier sinistre",
            "prise en charge", "indemnisation", "expert", "expertise",
            "réparation", "garage", "remorquage", "dépannage",
        ],
        "Bris de glace": [
            "bris de glace", "pare-brise", "parebrise", "vitre", "impact", "fissure",
            "remplacement pare-brise", "réparation pare-brise",
        ],
        "Vol / Vandalisme": [
            "vol", "cambriolage", "vandalisme", "effraction", "tentative de vol",
        ],
        "Contrat / Garanties": [
            "contrat", "garantie", "garanties", "couverture", "option", "niveau",
            "franchise", "exclusion", "conditions", "avenant", "résiliation",
        ],
        "Paiement / Cotisation": [
            "paiement", "prélèvement", "prélevé", "cotisation", "mensualité",
            "facture", "facturation", "tarif", "prix", "augmentation",
            "impayé", "rejet", "relance",
        ],
        "Compte / Accès": [
            "compte", "connexion", "login", "mot de passe", "authentification",
            "espace client", "application", "app", "accès", "bloqué",
        ],
        "Autre": [],
        "Inconnu": [],
    },
}


# =========================================================
# 4) TEXTE: normalisation + extraction colonne "texte"
# =========================================================
def ensure_text(df: pd.DataFrame, preferred: Optional[str] = None) -> pd.DataFrame:
    """
    Ensure a canonical text column called 'texte' exists.
    If preferred is provided and present, use it.
    Otherwise pick best among common candidates.
    """
    out = df.copy()

    if "texte" in out.columns:
        out["texte"] = out["texte"].fillna("").astype(str)
        return out

    candidates = [preferred] if preferred else []
    candidates += ["commentaire", "verbatim", "message", "content", "feedback", "review", "avis"]
    candidates = [c for c in candidates if c]

    text_col = None
    for c in candidates:
        if c in out.columns:
            text_col = c
            break

    if text_col is None:
        out["texte"] = ""
        return out

    out["texte"] = out[text_col].fillna("").astype(str)
    return out


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokenize_basic(text: str, min_len: int = 3) -> List[str]:
    text = _norm(text)
    text = re.sub(r"[^\w\sàâäçéèêëîïôöùûüÿ'-]", " ", text)
    tokens = [t.strip("'-") for t in text.split()]
    tokens = [t for t in tokens if len(t) >= min_len and not t.isdigit()]
    return tokens


def _stem_light(t: str) -> str:
    """
    Stemming light pour FR (approx).
    But: product-friendly, reduces noise.
    """
    for suf in (
        "ments", "ment", "ations", "ation", "iques", "ique", "ements", "ement",
        "euses", "euse", "eaux", "aux", "ées", "ée", "és", "é", "es", "e", "s"
    ):
        if len(t) > 5 and t.endswith(suf):
            return t[: -len(suf)]
    return t


# =========================================================
# 5) STOPWORDS STATISTIQUES (dataset-dependent)
# =========================================================
@st.cache_data(show_spinner=False)
def compute_stat_stopwords(df: pd.DataFrame, max_df_ratio: float = 0.60, min_len: int = 3) -> Set[str]:
    """
    Remove tokens that appear in >= max_df_ratio of documents (messages).
    This removes dataset-specific filler words.
    """
    if df is None or df.empty or "texte" not in df.columns:
        return set()

    total = len(df)
    if total <= 0:
        return set()

    doc_freq: Dict[str, int] = {}
    for txt in df["texte"].fillna("").astype(str).tolist():
        toks = set(_tokenize_basic(txt, min_len=min_len))
        for t in toks:
            if t in STOPWORDS_FR or t.isdigit():
                continue
            doc_freq[t] = doc_freq.get(t, 0) + 1

    threshold = int(total * max_df_ratio)
    if threshold <= 0:
        return set()

    return {t for t, c in doc_freq.items() if c >= threshold}


def tokenize(text: str, stat_stopwords: Optional[Set[str]] = None, min_len: int = 3) -> List[str]:
    toks = _tokenize_basic(text, min_len=min_len)
    ss = stat_stopwords or set()
    out: List[str] = []
    for t in toks:
        if t in STOPWORDS_FR:
            continue
        if t in DYNAMIC_STOPWORDS:
            continue
        if t in ss:
            continue
        out.append(_stem_light(t))
    return out


# =========================================================
# 6) THEMES (ultra explicable)
# =========================================================
def _score_theme(text: str, keywords: List[str]) -> Tuple[int, List[str]]:
    """
    Substring matching (phrases + single words).
    Returns (score, matched_keywords).
    """
    low = _norm(text)
    matched: List[str] = []
    for kw in keywords:
        kw_low = _norm(kw)
        if kw_low and kw_low in low:
            matched.append(kw)
    return len(matched), matched


@st.cache_data(show_spinner=False)
def infer_theme_from_text(
    df: pd.DataFrame,
    domain: Optional[str] = None,
    preferred_text_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Infer 'theme' from keywords on 'texte' (if theme not present).
    Adds explainability:
      - theme_score (number of matched keywords)
      - matched_keywords (comma-separated, top 8)
    Also ensures 'texte' exists.
    """
    out = ensure_text(df, preferred=preferred_text_col)

    # normalize motif -> theme
    if "motif" in out.columns and "theme" not in out.columns:
        out = out.rename(columns={"motif": "theme"})

    dom = (domain or "default").lower()
    mapping = KEYWORDS_BY_DOMAIN.get(dom, KEYWORDS_BY_DOMAIN["default"])
    theme_names = list(mapping.keys())

    def best_assign(txt: str) -> Tuple[str, int, str]:
        best_theme = "Autre"
        best_score = 0
        best_matches: List[str] = []

        for th in theme_names:
            kws = mapping.get(th, [])
            if not kws:
                continue
            score, matches = _score_theme(txt, kws)
            if score > best_score:
                best_score = score
                best_theme = th
                best_matches = matches

        if best_score <= 0:
            return "Autre", 0, ""

        return best_theme, best_score, ", ".join(best_matches[:8])

    # If theme exists, compute explainability relative to that theme when possible
    if "theme" in out.columns:
        def explain_row(row) -> Tuple[int, str]:
            txt = str(row.get("texte", ""))
            th = str(row.get("theme", "Autre"))
            kws = mapping.get(th, [])
            if not kws:
                _, sc, mk = best_assign(txt)
                return sc, mk
            sc, matches = _score_theme(txt, kws)
            return sc, ", ".join(matches[:8])

        exp = out.apply(lambda r: explain_row(r), axis=1, result_type="expand")
        out["theme_score"] = exp[0]
        out["matched_keywords"] = exp[1]
        return out

    assigned = out["texte"].astype(str).map(best_assign)
    out["theme"] = assigned.map(lambda x: x[0])
    out["theme_score"] = assigned.map(lambda x: x[1])
    out["matched_keywords"] = assigned.map(lambda x: x[2])
    return out


# =========================================================
# 7) WORDS TOP + CO-OCCURRENCE (auto + intelligents)
# =========================================================
@st.cache_data(show_spinner=False)
def compute_words_top(df: pd.DataFrame, n: int = 80, max_df_ratio: float = 0.60) -> pd.DataFrame:
    """
    Returns top tokens after:
      - stopwords FR
      - dynamic stopwords
      - statistical stopwords (tokens appearing in >= max_df_ratio documents)
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["word", "count"])

    df2 = ensure_text(df)
    stat_sw = compute_stat_stopwords(df2, max_df_ratio=max_df_ratio)

    tokens = df2["texte"].astype(str).map(lambda x: tokenize(x, stat_stopwords=stat_sw))
    flat = [t for row in tokens.tolist() for t in row]

    if not flat:
        return pd.DataFrame(columns=["word", "count"])

    s = pd.Series(flat).value_counts().head(int(n)).reset_index()
    s.columns = ["word", "count"]
    return s


@st.cache_data(show_spinner=False)
def compute_cooccurrence_top(df: pd.DataFrame, n_pairs: int = 60, max_df_ratio: float = 0.60) -> pd.DataFrame:
    """
    Co-occurrence table:
      word_1, word_2, count
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["word_1", "word_2", "count"])

    df2 = ensure_text(df)
    stat_sw = compute_stat_stopwords(df2, max_df_ratio=max_df_ratio)

    tokens_list = df2["texte"].astype(str).map(lambda x: tokenize(x, stat_stopwords=stat_sw)).tolist()
    counts: Dict[Tuple[str, str], int] = {}

    for tokens in tokens_list:
        uniq = sorted(set(tokens))
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                a, b = uniq[i], uniq[j]
                counts[(a, b)] = counts.get((a, b), 0) + 1

    if not counts:
        return pd.DataFrame(columns=["word_1", "word_2", "count"])

    out = (
        pd.DataFrame([{"word_1": k[0], "word_2": k[1], "count": v} for k, v in counts.items()])
        .sort_values("count", ascending=False)
        .head(int(n_pairs))
        .reset_index(drop=True)
    )
    return out
