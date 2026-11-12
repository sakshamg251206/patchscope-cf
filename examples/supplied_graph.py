"""Put a code graph PatchScope did not build through the same counterfactual test.

The degree-preserving null is the instrument, and it does not care where the edges came
from. This demonstrates that on a graph supplied as a file: a call graph, an embedding
k-NN graph, or a competition-supplied code graph can be substituted the same way.

Credential-free and network-free; it indexes this toolkit's own source. No benchmark
result is implied.
"""
import csv
from pathlib import Path

from patchscope.graph import load_edges, rewire
from patchscope.index import build_index
from patchscope.retrieve import rank


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    files = {str(path.relative_to(root)): path.read_text()
             for path in sorted((root / 'patchscope').glob('*.py'))}
    index = build_index(files)

    # Export this snapshot's import graph in the interchange format, then read it back.
    # Round-tripping is the check that a supplied graph is treated exactly like a built-in
    # one: anything that survives this is scored on identical terms.
    edges_file = root / 'examples' / 'supplied_graph_edges.csv'
    with edges_file.open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['source', 'target'])
        writer.writerows(sorted(index.graph.edges))
    supplied, audit = load_edges(edges_file, index.paths)
    assert set(supplied.edges) == set(index.graph.edges)
    assert set(supplied) == set(index.graph)

    # Identical edges must therefore produce identical rankings.
    scores = [1.0 / (i + 1) for i in range(len(index.paths))]
    assert rank(index.paths, scores, supplied, budget=10) == \
           rank(index.paths, scores, index.graph, budget=10)

    # And the supplied graph goes through the same degree-preserving null.
    null, stats = rewire(supplied, seed=2026)
    assert dict(null.in_degree()) == dict(index.graph.in_degree())
    assert dict(null.out_degree()) == dict(index.graph.out_degree())

    print(f'supplied graph: {audit["retained_edges"]} of {audit["supplied_edges"]} edges '
          f'retained over {len(index.paths)} indexed files')
    print(f'degree-preserving null: {stats["successful_swaps"]} swaps, '
          f'{stats["retained_edge_fraction"]:.1%} of edges unchanged, every degree held fixed')
    print('Round trip exact: a supplied graph is ranked and controlled identically.')
    print(f'\nTo score a supplied graph over real issues, put one <instance_id>.csv per issue\n'
          f'in a directory and run:\n'
          f'  patchscope evaluate --sample 40 --graph-edges <dir> --output results/supplied')
    edges_file.unlink()


if __name__ == '__main__':
    main()
