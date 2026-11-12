"""Ranking has no access to labels, patches or evaluation metadata."""
from collections import Counter, defaultdict
import math
import numpy as np


class BM25:
    """Positive-IDF BM25, k1=1.5, b=0.75; repeated query terms count once."""
    def __init__(self, documents: list[list[str]]):
        if not documents:
            raise ValueError('empty index')
        self.n = len(documents)
        lengths = np.array([len(doc) for doc in documents], dtype=float)
        average = max(float(lengths.mean()), 1.)
        normalization = 1.5 * (.25 + .75 * lengths / average)
        self.postings = defaultdict(list)
        for i, document in enumerate(documents):
            for token, count in Counter(document).items():
                self.postings[token].append((i, count * 2.5 / (count + normalization[i])))
        self.idf = {token: math.log(1 + (self.n - len(postings) + .5) / (len(postings) + .5))
                    for token, postings in self.postings.items()}

    def scores(self, query: list[str]) -> np.ndarray:
        scores = np.zeros(self.n)
        for token in sorted(set(query)):
            if token in self.postings:
                for i, weight in self.postings[token]:
                    scores[i] += self.idf[token] * weight
        return scores


def rank(paths: list[str], scores: np.ndarray, graph=None, budget=100, seeds=20, alpha=.5) -> list[str]:
    if budget < 1 or seeds < 1 or not 0 <= alpha <= 1:
        raise ValueError('positive budgets and alpha in [0,1] required')
    if len(paths) != len(scores) or not np.all(np.isfinite(scores)):
        raise ValueError('invalid scores')
    order = sorted(range(len(paths)), key=lambda i: (-scores[i], paths[i]))
    pool = order[:budget]
    if graph is None or alpha == 0 or not pool:
        return [paths[i] for i in pool]
    maximum = max(float(scores[order[0]]), 1e-12)
    lexical = {paths[i]: float(scores[i]) / maximum for i in pool}
    graph_score = dict.fromkeys(lexical, 0.)
    for i in order[:min(seeds, len(pool))]:
        path = paths[i]
        neighbors = sorted(graph.successors(path))
        if neighbors:
            weight = float(scores[i]) / maximum / len(neighbors)
            for neighbor in neighbors:
                if neighbor in graph_score:
                    graph_score[neighbor] += weight
    # One-hop residual transfer; no query/label-based tuning, no pool expansion.
    combined = {p: lexical[p] + alpha * graph_score[p] for p in lexical}
    return sorted(lexical, key=lambda p: (-combined[p], p))
