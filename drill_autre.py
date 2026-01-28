from pathlib import Path
import pandas as pd
import re
from collections import Counter

p = Path("insightia/data/commentaires_topics.csv")
df = pd.read_csv(p)

autre = df[df["theme"].astype(str).str.strip().str.lower() == "autre"].copy()

def tokens(s: str):
    s = str(s).lower()
    s = re.sub(r"[^a-zàâçéèêëîïôùûüÿñæœ0-9\s]", " ", s)
    t = [w for w in s.split() if len(w) >= 4]
    return t

# tokens sur text_norm si dispo, sinon texte
col = "text_norm" if "text_norm" in autre.columns else "texte"
all_tokens = []
for x in autre[col].fillna(""):
    all_tokens.extend(tokens(x))

print("Nb verbatims 'Autre':", len(autre))

print("\nTOP 30 MOTS (Autre):")
for w, c in Counter(all_tokens).most_common(30):
    print(f"{w:20s} {c}")

# bigrammes
bigrams = []
for x in autre[col].fillna(""):
    t = tokens(x)
    bigrams.extend(zip(t, t[1:]))

print("\nTOP 30 BIGRAMMES (Autre):")
for (a, b), c in Counter(bigrams).most_common(30):
    print(f"{a} {b:15s} {c}")
