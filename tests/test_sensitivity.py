"""Guards the dev-only sensitivity sweep's aggregation grid."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'dev_sensitivity.py'


@pytest.fixture(scope='module')
def sensitivity():
    spec = importlib.util.spec_from_file_location('dev_sensitivity', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_aggregate_covers_every_grid_cell_and_averages_within_cell(sensitivity):
    records = []
    for alpha in sensitivity.ALPHAS:
        for seeds in sensitivity.SEED_BUDGETS:
            for method in ('real', 'rewired', 'real_reverse'):
                for value in (0.0, 1.0):  # two issues per cell; mean must be 0.5
                    records.append(dict(instance_id=f'i{value}', repo='r', method=method,
                                        alpha=alpha, seed_budget=seeds,
                                        hit1=value, hit5=value, hit10=value, mrr10=value))
    table = sensitivity.aggregate(records)
    assert len(table) == len(sensitivity.ALPHAS) * len(sensitivity.SEED_BUDGETS) * 3
    assert {(r['method'], r['alpha'], r['seed_budget']) for r in table} == {
        (m, a, s) for m in ('real', 'rewired', 'real_reverse')
        for a in sensitivity.ALPHAS for s in sensitivity.SEED_BUDGETS}
    assert all(r['n'] == 2 and r['hit5'] == pytest.approx(0.5) for r in table)


def test_alpha_zero_is_the_lexical_baseline_for_every_method(sensitivity):
    """alpha=0 must disable the graph, so all methods coincide; the sweep relies on this."""
    import numpy as np
    from patchscope.retrieve import rank
    import networkx as nx

    paths = ['a.py', 'b.py', 'c.py']
    scores = np.array([3.0, 2.0, 1.0])
    graph = nx.DiGraph()
    graph.add_nodes_from(paths)
    graph.add_edge('a.py', 'c.py')
    baseline = rank(paths, scores, None, 3, 2, 0.5)
    assert rank(paths, scores, graph, 3, 2, 0.0) == baseline
    assert rank(paths, scores, graph.reverse(copy=True), 3, 2, 0.0) == baseline
    assert rank(paths, scores, graph, 3, 2, 0.5) != baseline  # the graph does move ranks
