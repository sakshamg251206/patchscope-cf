from collections import Counter

import networkx as nx
import numpy as np
import pytest

from patchscope.index import build_index, tokenize
from patchscope.graph import rewire, edge_drop
from patchscope.retrieve import BM25, rank
from patchscope.masking import mask_query


FILES = {
    'pkg/__init__.py': 'from . import core\n',
    'pkg/core.py': 'from .helper import work\nclass CamelClass:\n    """Core computation."""\n    def snake_method(self): return work()\n',
    'pkg/helper.py': 'def work():\n    """Useful helper."""\n    return 1\n',
    'pkg/sub/__init__.py': '',
    'pkg/sub/use.py': 'from .. import core\nimport pkg.helper\nimport numpy\n',
    'pkg/broken.py': 'def old(:\n',
}


def test_tokenizer_and_ast_import_resolution():
    assert tokenize('CamelClass snake_case HTTPError') == ['camel', 'class', 'snake', 'case', 'http', 'error']
    index = build_index(FILES)
    assert index.paths == sorted(FILES)
    assert set(index.graph.edges) == {('pkg/__init__.py', 'pkg/core.py'),
        ('pkg/core.py', 'pkg/helper.py'), ('pkg/sub/use.py', 'pkg/core.py'),
        ('pkg/sub/use.py', 'pkg/helper.py')}
    assert index.audit['parse_failures'] == ['pkg/broken.py']
    assert 'computation' in index.tokens[index.paths.index('pkg/core.py')]
    assert all(attrs['kind'] == 'import' for *_, attrs in index.graph.edges(data=True))


def test_rewiring_preserves_degrees_nodes_and_determinism():
    graph = nx.DiGraph()
    graph.add_nodes_from(range(25))
    graph.add_edges_from((i, (i+j) % 25) for i in range(25) for j in (1, 3, 5))
    a, stats = rewire(graph, 2026)
    b, _ = rewire(graph, 2026)
    assert set(a) == set(graph)
    assert dict(a.in_degree()) == dict(graph.in_degree())
    assert dict(a.out_degree()) == dict(graph.out_degree())
    assert not list(nx.selfloop_edges(a))
    assert set(a.edges) == set(b.edges)
    assert set(a.edges) != set(graph.edges)
    assert stats['successful_swaps'] > 0
    empty, stats = rewire(nx.empty_graph(3, create_using=nx.DiGraph), 1)
    assert len(empty) == 3 and stats['successful_swaps'] == 0
    dropped = edge_drop(graph, 1)
    assert len(dropped.edges) == len(graph.edges) // 2
    assert set(dropped) == set(graph)


def test_bm25_known_formula_empty_query_and_shared_pool():
    model = BM25([['a', 'a'], ['b']])
    score = model.scores(['a'])
    expected = np.log(1 + 1.5 / 1.5) * (2 * 2.5) / (2 + 1.5*(.25+.75*2/1.5))
    assert score[0] == pytest.approx(expected)
    assert score[1] == 0
    assert np.all(model.scores([]) == 0)
    paths = ['a', 'b', 'c', 'd']
    scores = np.array([4., 3., 2.1, 1.])
    graph = nx.DiGraph([('a', 'c'), ('a', 'd')])
    graph.add_nodes_from(paths)
    baseline = rank(paths, scores, None, budget=3, seeds=1)
    real = rank(paths, scores, graph, budget=3, seeds=1)
    assert baseline == ['a', 'b', 'c']
    assert real == ['a', 'c', 'b']
    assert set(real) == set(baseline)  # identical candidate pool, not just count
    assert rank(paths, scores, nx.empty_graph(paths, create_using=nx.DiGraph), budget=3) == baseline
    assert rank(paths, scores, graph, budget=3, alpha=0) == baseline
    assert rank(paths, scores, graph, budget=3, seeds=1) == real


def test_guarded_masking_spans_and_ambiguity():
    paths = ['pkg/odd_name.py', 'pkg/x/core.py', 'pkg/y/core.py', 'pkg/io.py']
    text = 'pkg/odd_name.py pkg.odd_name odd_name.py odd_name core io action'
    masked, spans = mask_query(text, ['pkg/odd_name.py', 'pkg/x/core.py', 'pkg/io.py'], paths)
    assert 'pkg/odd_name.py' not in masked
    assert 'pkg.odd_name' not in masked
    assert 'odd_name' not in masked
    assert ' core io action' in masked
    assert len(spans) == 4
    assert all(text[s['start']:s['end']] == s['text'] for s in spans)


def test_src_and_lib_layout_absolute_imports():
    index = build_index({'lib/pkg/a.py': 'import pkg.b', 'lib/pkg/b.py': 'x=1'})
    assert set(index.graph.edges) == {('lib/pkg/a.py', 'lib/pkg/b.py')}
    index = build_index({'src/pkg/a.py': 'from pkg.b import x', 'src/pkg/b.py': 'x=1'})
    assert set(index.graph.edges) == {('src/pkg/a.py', 'src/pkg/b.py')}


def test_mask_actual_modules_in_src_layout_and_package_initializers():
    files = ['lib/pkg/abc.py', 'sphinx/ext/autodoc/__init__.py']
    query = 'lib/pkg/abc.py pkg.abc sphinx.ext.autodoc sphinx/ext/autodoc/__init__.py'
    masked, spans = mask_query(query, files, files)
    assert not masked.strip()
    assert len(spans) == 4
