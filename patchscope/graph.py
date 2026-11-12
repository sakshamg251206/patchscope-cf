"""Directed topology interventions; preserve all nodes including isolates.

The interventions here take any directed graph over the indexed file set, so a code graph
produced elsewhere -- a call graph, a competition-supplied graph, an embedding k-NN graph --
can be put through the same degree-preserving null as the built-in import graph. Load one
with `load_edges`.
"""
import csv
import json
import random
from pathlib import Path
from typing import Iterable

import networkx as nx


def load_edges(path: Path, nodes: Iterable[str]) -> tuple[nx.DiGraph, dict]:
    """Load an externally supplied code graph as directed edges over the indexed files.

    `path` is either a CSV with a `source,target` header or a JSON list of `[source, target]`
    pairs, both holding repository-relative file paths. Every indexed file becomes a node, so
    the supplied graph is scored over exactly the same file set as the built-in import graph
    and the two are directly comparable. Edges touching a file this snapshot does not index
    are dropped and counted.

    The audit reports that drop because a mismatched path convention would otherwise be
    indistinguishable from a graph that simply carries no signal.
    """
    nodes = list(nodes)
    allowed = set(nodes)
    if path.suffix == '.json':
        pairs = [(str(a), str(b)) for a, b in json.loads(path.read_text())]
    else:
        with path.open(newline='') as handle:
            reader = csv.DictReader(handle)
            missing = {'source', 'target'} - set(reader.fieldnames or ())
            if missing:
                raise ValueError(f'{path}: CSV needs source,target columns; missing {sorted(missing)}')
            pairs = [(row['source'], row['target']) for row in reader]
    kept = sorted({(a, b) for a, b in pairs if a in allowed and b in allowed and a != b})
    if pairs and not kept:
        raise ValueError(
            f'{path}: none of the {len(pairs)} supplied edges connect two indexed files. '
            'Paths must be repository-relative and match the base-commit snapshot.')
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from((a, b, dict(kind='external', confidence='supplied')) for a, b in kept)
    unknown = sorted({e for pair in pairs for e in pair if e not in allowed})
    return graph, dict(source=str(path), supplied_edges=len(pairs), retained_edges=len(kept),
                       retained_fraction=len(kept) / len(pairs) if pairs else 0.,
                       unknown_endpoints=len(unknown), unknown_examples=unknown[:10])


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
