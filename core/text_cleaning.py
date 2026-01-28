from __future__ import annotations
import re
from typing import Iterable, List


def clean_text_fast(texts: Iterable[str]) -> List[str]:
    """
    Nettoyage léger et rapide (proche de ton implémentation initiale).
    - lower
    - suppression chiffres
    - conservation des caractères FR
    - normalisation espaces
    """
    out: List[str] = []
    for t in texts:
        t = "" if t is None else str(t)
        t = t.lower()
        t = re.sub(r"\d+", " ", t)
        t = re.sub(r"[^\w\sàâçéèêëîïôûùüÿñæœ-]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        out.append(t)
    return out
