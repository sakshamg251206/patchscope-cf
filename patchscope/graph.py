"""Directed topology interventions; preserve all nodes including isolates."""
import random
import networkx as nx


def rewire(graph: nx.DiGraph, seed: int, swaps_per_edge: int = 5):
    rng = random.Random(seed)
    result = graph.copy()
    edges = sorted(graph.edges)
    requested = swaps_per_edge * len(edges)
    successful = attempts = 0
    if len(edges) >= 2:
        while successful < requested and attempts < requested * 20:
            attempts += 1
            i, j = rng.sample(range(len(edges)), 2)
            a, b = edges[i]
            c, d = edges[j]
            if a == c or b == d or a == d or c == b:
                continue
            if result.has_edge(a, d) or result.has_edge(c, b):
                continue
            result.remove_edge(a, b)
            result.remove_edge(c, d)
            result.add_edge(a, d, kind='rewired', confidence='control')
            result.add_edge(c, b, kind='rewired', confidence='control')
            edges[i], edges[j] = (a, d), (c, b)
            successful += 1
    assert set(result) == set(graph)
    assert dict(result.in_degree()) == dict(graph.in_degree())
    assert dict(result.out_degree()) == dict(graph.out_degree())
    retained = len(set(result.edges) & set(graph.edges))
    return result, dict(seed=seed, requested_swaps=requested, successful_swaps=successful,
                        attempts=attempts, retained_edge_fraction=retained / len(edges) if edges else 1.)


def edge_drop(graph: nx.DiGraph, seed: int) -> nx.DiGraph:
    result = graph.copy()
    edges = sorted(result.edges)
    random.Random(seed).shuffle(edges)
    result.remove_edges_from(edges[len(edges)//2:])
    return result
