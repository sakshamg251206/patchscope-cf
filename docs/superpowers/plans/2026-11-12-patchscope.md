# PatchScope-CF Implementation Plan

> Execute inline under executing-plans and test-driven-development. User explicitly requests autonomous execution without approval pauses.

**Goal:** Deliver a real, reproducible frozen-commit localization benchmark and measured Kaggle paper.
**Architecture:** Separate data/labels from a gold-blind AST index and retrieval API. Evaluate fixed ranking rules on an immutable selection; derive reporting from saved rows.
**Tech Stack:** Python 3.11+, NumPy, NetworkX, matplotlib, pytest; standard-library HTTP and git.
**Spec:** docs/PROJECT_SPEC.md (user-provided full design).

## Global Constraints
- No publication without explicit permission; no untrusted setup scripts.
- Only base-commit source enters retrieval; patches only form labels and diagnostic masking.
- Freeze selection before test performance. Seed 2026; three rewiring seeds; 1000+ paired bootstrap samples.
- All methods share eligible cohort, lexical index, seed scores, candidate count and output budgets.
- Preserve 90 minutes before stated 23:59 UTC deadline; writeup <=3000 words.

## Review Focus
- Deleted/new/renamed/quoted paths and unsafe paths in gold labels.
- Relative imports, package initializers and syntax errors in historical Python.
- Sparse graphs cannot necessarily achieve requested swaps: record actual counts.
- Network/cache corruption and absence of base-commit source labels.
- Label-informed masking is a diagnostic, and issue-level CIs ignore repository clustering.

### Task 1: Source labels and reproducible data
Files: pyproject.toml, .gitignore, patchscope/data.py, labels.py; tests/test_data.py.
Interfaces: source_path(path), gold_paths(patch); fetch_dataset(cache), freeze_selection(rows, sample, seed); snapshot(repo, commit, cache).
- [x] Write and run failing tests for source filters, patch edge cases, immutable deterministic selection and exact snapshot cache.
- [x] Implement metadata download with pinned HF revision, retry/timeouts; select 40 shuffled test IDs from all 300 before labels; record every exclusion without replacement.
- [x] Test fixtures and one real frozen commit. Record source hashes and limits.

### Task 2: Index and graph controls
Files: patchscope/index.py, graph.py, retrieve.py, masking.py; tests/test_core.py.
Interfaces: build_index(files) returns sorted paths, tokens, import graph, audit; BM25(tokens).scores(query); rank(scores, graph, M=20, budget=100, alpha=0.5); rewire(graph, seed); mask_query(text, gold, paths).
- [x] Write failing tests for tokenizer, relative imports, in/out degree preservation, graph-off identity, deterministic rankings, exact budgets and guarded masks.
- [x] Implement AST names/imports/docstrings capped per file, positive-IDF BM25 and one-hop propagation. Fixed lexically chosen candidate pool makes graph intervention pool-identical.
- [x] Run all unit tests; print actual top ten and gold labels for one issue.

### Task 3: Evaluation and execution
Files: patchscope/evaluate.py, cli.py; tests/test_evaluate.py; scripts/run_smoke.sh, run_experiments.sh.
Interfaces: evaluate(sample, seed, output, split), metrics(predictions, gold), paired_bootstrap(real, control).
- [x] Write failing metric, pairing, leakage-boundary and end-to-end fixture tests.
- [x] Implement auditable CSV/config outputs, runtime separation, checkpoints and invariant checks. Defaults precommitted, no test tuning; dev descriptive calibration only.
- [x] Run >=5 test smoke issues then fixed 40 test and all dev; record failures explicitly.

### Task 4: Reports and release
Files: patchscope/report.py; README.md, LICENSE, examples/demo.py; paper/*.md; results/*.
- [x] Verify reporting against known synthetic metric fixture, then generate from real results.
- [x] Verify official pages and related literature; document discrepancies and access failures.
- [x] Write measured paper with uncertainty and examples, license/data notices and exact reproducible commands.
- [x] Run pytest, README install/demo, consistency audit, word count and final independent review.

## Rulings / progress
- Initial repository is empty; no existing callers, fixtures, configs or data to preserve.
- Use Python 3.12 through uv if available; otherwise current 3.14 meets floor.
- Candidate-pool control: fixed top-100 BM25 pool for every method; graph transfers from top-20 seeds only within that pool. This sacrifices graph discovery beyond 100 to remove pool-composition confounding.
- Optional Gemma, adaptive tuning and competition embeddings omitted until core completed.

Final verification: 20 tests passed; corrected main40/7repos/0excluded, dev23/6repos/0excluded; full reproduction matches all480 rows excluding timing. Independent code review and subsequent final factual review in paper/CODE_REVIEW.md. Original pre-review outputs retained.
