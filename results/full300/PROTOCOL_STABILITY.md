# Protocol stability after the supplied-graph interface was added

`results/full300/` was produced before `--graph-edges` existed. The change touched
`graph.py` (added `load_edges`), `evaluate.py` (an optional `graph_edges` argument) and
`cli.py` (the flag), so the module hashes in `experiment_config.json` no longer match the
current working tree. Behaviour did not change.

**Evidence.** With no `--graph-edges` argument, `graph_edges` is `None`, `load_edges` is
never called, and `index.graph` is the built-in import graph exactly as before. Checked
empirically on current code:

```sh
patchscope evaluate --sample 5 --seed 2026 --split test --output /tmp/inertness
```

re-ran the first five issues of the same deterministic cohort and produced **60 of 60 rows
with `predicted_paths` byte-identical** to the corresponding rows in
`results/full300/per_instance.csv` — zero ranking disagreements across every condition,
method and control seed.

`python scripts/verify_results.py results/full300` continues to pass on current code
(299 issues, 12 repositories, 3,588 rows).

No number in the paper was regenerated for this change.
