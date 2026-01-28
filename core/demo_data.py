from __future__ import annotations

from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent  # insightia/
DEMO_DIR = BASE_DIR / "assets" / "demo"

DEMO_ECOM_PATH = DEMO_DIR / "demo_insightia_ecommerce.csv"
DEMO_SAAS_PATH = DEMO_DIR / "demo_insightia_saas.csv"


def load_demo_ecommerce() -> pd.DataFrame:
    if not DEMO_ECOM_PATH.exists():
        raise FileNotFoundError(
            f"Fichier introuvable: {DEMO_ECOM_PATH}. "
            "Ajoute le CSV dans insightia/assets/demo/"
        )
    return pd.read_csv(DEMO_ECOM_PATH)


def load_demo_saas() -> pd.DataFrame:
    if not DEMO_SAAS_PATH.exists():
        raise FileNotFoundError(
            f"Fichier introuvable: {DEMO_SAAS_PATH}. "
            "Ajoute le CSV dans insightia/assets/demo/"
        )
    return pd.read_csv(DEMO_SAAS_PATH)


def load_demo_minimal() -> pd.DataFrame:
    # Fallback simple si besoin (ne remplace pas les 2 CSV démo)
    return pd.DataFrame({
        "id": ["DEMO-0001","DEMO-0002","DEMO-0003","DEMO-0004"],
        "date": ["2025-11-01","2025-11-02","2025-11-03","2025-11-04"],
        "canal": ["App","Web","Email","Chat"],
        "csat": [1,2,2,4],
        "commentaire": [
            "Impossible de me connecter, ça bloque au login.",
            "Le paiement échoue avec ma carte, urgent.",
            "Livraison en retard, colis non reçu.",
            "Très satisfaite du service, merci !",
        ],
    })
