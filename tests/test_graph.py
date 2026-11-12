"""Supplied code graphs: loading, validation, and the degree-preserving null."""
import pytest

from patchscope.graph import load_edges, rewire


def test_load_edges_builds_a_graph_over_the_indexed_files(tmp_path):
    """A supplied edge list becomes a graph on exactly the indexed node set."""
    edges = tmp_path / 'case.csv'
    edges.write_text('source,target\na.py,b.py\nb.py,c.py\na.py,a.py\n')
    graph, audit = load_edges(edges, ['a.py', 'b.py', 'c.py', 'lonely.py'])
    assert set(graph) == {'a.py', 'b.py', 'c.py', 'lonely.py'}       # isolates preserved
    assert set(graph.edges) == {('a.py', 'b.py'), ('b.py', 'c.py')}  # self-loop dropped
    assert audit['supplied_edges'] == 3 and audit['retained_edges'] == 2


def test_load_edges_drops_and_counts_unindexed_endpoints(tmp_path):
    """Files outside the snapshot cannot be ranked, so their edges are dropped and reported."""
    edges = tmp_path / 'case.json'
    edges.write_text('[["a.py", "b.py"], ["a.py", "gone.py"]]')
    graph, audit = load_edges(edges, ['a.py', 'b.py'])
    assert set(graph.edges) == {('a.py', 'b.py')}
    assert audit['unknown_endpoints'] == 1 and audit['unknown_examples'] == ['gone.py']


def test_load_edges_rejects_a_path_convention_that_matches_nothing(tmp_path):
    """Silently returning an empty graph would read as 'the graph carries no signal'."""
    edges = tmp_path / 'case.csv'
    edges.write_text('source,target\n/abs/a.py,/abs/b.py\n')
    with pytest.raises(ValueError, match='repository-relative'):
        load_edges(edges, ['a.py', 'b.py'])


def test_a_supplied_graph_survives_the_degree_preserving_null(tmp_path):
    """The whole point: a supplied graph goes through the same rewiring control."""
    edges = tmp_path / 'case.csv'
    edges.write_text('source,target\n' + ''.join(f'f{i}.py,f{i+1}.py\n' for i in range(6)))
    graph, _ = load_edges(edges, [f'f{i}.py' for i in range(7)])
    null, stats = rewire(graph, seed=2026)
    assert dict(null.in_degree()) == dict(graph.in_degree())
    assert dict(null.out_degree()) == dict(graph.out_degree())
    assert stats['successful_swaps'] > 0
