from pathlib import Path
import pandas as pd

p = Path("insightia/data/commentaires_topics.csv")
df = pd.read_csv(p)

print("✅ Colonnes :")
print(df.columns.tolist())

print("\n✅ Aperçu (5 lignes) :")
print(df.head(5))

# Vérif des colonnes clés attendues par scoring.py
expected = ["theme", "sentiment", "blocking", "low_confidence"]
print("\n✅ Colonnes clés présentes ?")
for c in expected:
    print(c, "=>", c in df.columns)

# Valeurs possibles (si colonne existe)
if "sentiment" in df.columns:
    print("\n✅ Valeurs sentiment (top) :")
    print(df["sentiment"].value_counts().head(10))

if "blocking" in df.columns:
    print("\n✅ Valeurs blocking (top) :")
    print(df["blocking"].value_counts().head(10))
