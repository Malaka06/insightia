from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import csr_matrix


@dataclass(frozen=True)
class ClusteringParams:
    n_topics: int = 12
    max_features: int = 8000
    ngram_range: Tuple[int, int] = (1, 2)
    min_df: int = 2
    random_state: int = 42
    n_init: int = 10
    top_n_words: int = 3


@dataclass(frozen=True)
class ClusteringResult:
    topics: np.ndarray                 # shape (n_samples,)
    topic_labels: Dict[int, str]       # topic_id -> label
    feature_names: np.ndarray          # tf-idf vocabulary terms


def compute_topic_labels_from_X(
    X: csr_matrix,
    topic_np: np.ndarray,
    feature_names: np.ndarray,
    top_n_words: int = 3
) -> Dict[int, str]:
    labels: Dict[int, str] = {}
    for t in np.unique(topic_np):
        rows = np.where(topic_np == t)[0]
        if len(rows) == 0:
            labels[int(t)] = f"Topic {int(t)}"
            continue
        mean_tfidf = X[rows].mean(axis=0).A1
        top_terms = feature_names[mean_tfidf.argsort()[-top_n_words:]][::-1]
        labels[int(t)] = " / ".join(top_terms.tolist())
    return labels


def run_kmeans_tfidf(texts: List[str], params: ClusteringParams) -> ClusteringResult:
    if not texts:
        raise ValueError("Liste de textes vide.")

    vectorizer = TfidfVectorizer(
        max_features=int(params.max_features),
        ngram_range=params.ngram_range,
        min_df=int(params.min_df),
    )
    X = vectorizer.fit_transform(texts)

    if X.shape[0] < params.n_topics:
        raise ValueError(
            f"Pas assez de lignes ({X.shape[0]}) pour {params.n_topics} thèmes. "
            f"Réduis le nombre de thèmes."
        )

    km = KMeans(
        n_clusters=int(params.n_topics),
        random_state=int(params.random_state),
        n_init=int(params.n_init),
    )
    topic_np = km.fit_predict(X)

    terms = np.array(vectorizer.get_feature_names_out())
    labels = compute_topic_labels_from_X(X, topic_np, terms, top_n_words=int(params.top_n_words))

    return ClusteringResult(
        topics=topic_np,
        topic_labels=labels,
        feature_names=terms,
    )
