# test_backlog.py
# Génère un backlog décisionnel à partir de commentaires_topics.csv

from pathlib import Path
import pandas as pd

# =========================
# 1) Chemins robustes
# =========================
# Dossier où se trouve CE fichier (insightia/data)
BASE_DIR = Path(__file__).resolve().parent

# Fichier d'entrée (dans le même dossier)
TOPICS_PATH = BASE_DIR / "commentaires_topics.csv"

# Fichier de sortie
BACKLOG_PATH = BASE_DIR / "backlog.csv"

# =========================
# 2) Vérification fichier
# =========================
if not TOPICS_PATH.exists():
    raise FileNotFoundError(
        f"❌ Fichier introuvable : {TOPICS_PATH}\n"
        f"➡️ Vérifie que 'commentaires_topics.csv' est bien dans insightia/data/"
    )

# =========================
# 3) Chargement des données
# =========================
topics = pd.read_csv(TOPICS_PATH)

# =========================
# 4) Import du moteur décisionnel
# =========================
from insightia.core.scoring import (
    theme_table,
    backlog_from_theme_table,
    ImpactWeights
)

# =========================
# 5) Construction du backlog
# =========================
# Agrégation par thème
theme_df = theme_table(topics)

# Poids explicites (tu pourras les ajuster ensuite)
weights = ImpactWeights(
    w_volume=0.40,
    w_blocking=0.35,
    w_neg=0.25
)

# Backlog décisionnel
backlog = backlog_from_theme_table(theme_df, weights=weights)

# =========================
# 6) Sauvegarde
# =========================
backlog.to_csv(BACKLOG_PATH, index=False, encoding="utf-8")

# =========================
# 7) Affichage de contrôle
# =========================
print("✅ BACKLOG GÉNÉRÉ AVEC SUCCÈS")
print(f"📄 Fichier : {BACKLOG_PATH}")
print("\n🔝 TOP 10 BACKLOG :")
print(backlog.head(10))
