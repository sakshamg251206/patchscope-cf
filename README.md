# PatchScope-CF

Do import graphs improve issue-to-file localization beyond lexical retrieval and node popularity? PatchScope-CF is a CPU-only audit toolkit that compares BM25, real import edges, directed-degree-preserving rewired edges, and edge deletion **inside exactly the same lexical candidate pool**. It indexes real SWE-bench Lite repositories at their pre-fix commits, records exclusions and masking spans, and produces paired results and bootstrap intervals. It evaluates file retrieval; it does not generate or validate patches.

## Install and one-minute local demo

Python 3.11+; measured environment: Python 3.12.4 on macOS arm64. The included `.python-version` selects Python 3.12 for the locked installation; avoid Python 3.14 with the pinned PyArrow version. Install [uv](https://docs.astral.sh/uv/) first if needed.

```sh
uv sync --locked --extra test
uv run --locked python examples/demo.py
uv run --locked pytest -q
```

The local demo uses this toolkit's own source files and an explicitly illustrative query. No credentials, model, GPU, external repository or benchmark download is needed. Dependencies and transitive versions are in `uv.lock`; `pyproject.toml` pins direct dependencies.

## Real benchmark smoke run

Requires network, git and disk space for cached git objects. Downloads only metadata and needed historical repository snapshots; never runs project setup code.

```sh
uv run --locked patchscope evaluate --sample 5 --seed 2026 --output results/demo
uv run --locked patchscope report --results results/demo
```

Output directories are immutable: repeat with a fresh `--output` directory. Interrupted runs retain prefix CSVs but are not reportable as complete. Cache data is under ignored `data/cache/`. Source repositories are bare caches; there is no checkout of the user's workspace.

## Exact main experiment

```sh
uv run --locked patchscope evaluate --sample 40 --seed 2026 \
  --manifest data/selection_manifest.json --output results/reproduction
uv run --locked patchscope report --results results/reproduction
```

The downloader and manifest pin Hugging Face revision `b0dde1093fe417d83b7184254edf8199c1f0dff5`. Selection refuses a mismatched cohort or revision rather than quietly changing the benchmark. The test subset is the first 40 IDs after sorting all 300 test IDs and shuffling with Python `random.Random(2026)`. Exclusions are recorded, never replaced. No test tuning occurred; the smoke cases are the first five of that same cohort and only tested pipeline correctness. The complete 23-case dev split is a separate descriptive run; its repositories do not overlap this test sample.

```sh
uv run --locked patchscope evaluate --sample 23 --seed 2026 --split dev --output results/dev_reproduction
uv run --locked patchscope report --results results/dev_reproduction
```

### Cold-cache tip

Snapshots are fetched one commit at a time with `git fetch --depth=1`. For
history-heavy repositories (matplotlib, astropy, django) a single full fetch is much
faster than dozens of shallow ones, and avoids slow-download timeouts:

```sh
cd data/cache/repos/matplotlib__matplotlib
git fetch --no-tags --unshallow origin '+refs/heads/*:refs/remotes/origin/*'
```

The evaluator checks for the commit locally before fetching, so a pre-warmed clone makes
the measured run network-free. Failed fetches are reported with the underlying git error
and are **infrastructure exclusions, not protocol exclusions**; rerun them rather than
reporting them as ineligible cases.

## Protocol and boundaries

- **Snapshot:** exact `base_commit` git objects. No patch is applied. Index cache is keyed by repository/commit, with source/tree checksums and verified source checksum on cache reuse. Labels come solely from solution-diff `+++` paths after selection. All filtered gold paths must exist in the indexed base snapshot; otherwise the case is excluded. Renamed/new paths absent at base cannot be localization labels here.
- **Source filter:** `.py` files only; exclude path components `tests`, `test`, `testing`, `docs`, `doc`, `generated`, `vendor`, `vendored`, `build`, `dist`, `.git`, `examples`, `benchmarks`, `_vendor*`; exclude `test_*`, `*_test.py`, `setup.py`, `conftest.py`, `conf.py`, `versioneer.py`. Exclude symlinks and files over 250,000 bytes; fail a snapshot above 20,000 eligible files. These are heuristic filters; some generated files can remain.
- **Index:** sorted file paths; path/module text and AST function/class/method names, imports and docstrings. First 24,000 characters per document. Historical parse failures retain path/module text and are logged. Recognizes root, `src/` and `lib/` module layouts. No call graph, embeddings, hints, future test patches or solution content.
- **Lexical:** positive-IDF BM25, `k1=1.5`, `b=0.75`. ASCII lowercase alphanumeric tokens, camel/acronym/snake splits, no stopword removal. Query tokens are deduplicated. Zero-score ties use path order.
- **Graph:** directed importer → imported module edges, exact resolvable internal modules only; relative imports supported. Imported submodules take precedence over containing modules. Dynamic imports, aliases/calls and nonstandard namespace/source roots are incomplete.
- **Ranking:** pool = top 100 BM25 files, seeds = top 20. With normalized lexical scores `l`, rank by `l(v) + 0.5 * sum(l(u)/outdegree(u))` over seed edges `u→v`. The degree denominator includes all graph successors, even outside the fixed pool. No multi-hop propagation or discoveries beyond the lexical pool. Return up to 100 paths; report k=1/5/10 and budget curves.
- **Controls:** three directed double-edge-swap runs (2026/2027/2028), five successful swaps per edge requested, at most 20 attempts per requested swap; reject loops/duplicates, assert every node's in/out degree. Log completed swaps and retained-edge fractions. Bounded swaps do not establish uniform null sampling. Edge-drop retains floor(E/2) edges with seed 2026; nodes remain.
- **Masking:** evaluation-only gold-informed removal of path, dotted module and guarded unique basename/stem; no bare stems under four characters or common ambiguous stems listed in `masking.py`. Save changed spans. This diagnostic is neither a deployment preprocessing rule nor a causal estimate by itself.
- **Timing:** query time includes tokenization/BM25 plus ranking, median of three warm measurements each. Rewired timing first averages seeds within an issue. Index, snapshots, and control construction are separately logged in `offline_times.csv`.
- **Uncertainty:** paired issue bootstrap, 2,000 replicates, seed 2026. Rewired seeds average *within* issue before aggregation. Issues from the same repository are correlated; intervals are descriptive and can understate repository-level uncertainty. Subgroup tables are exploratory.

## Measured pilot result

All 40 selected test issues across seven repositories were eligible; no case exclusions. Raw Hit@5: BM25 **65.0%**, real graph **47.5%**, rewired mean **50.8%**, edge-drop **50.0%**. Real minus rewired is −3.3 percentage points (95% paired issue-bootstrap interval −12.5 to +5.0): inconclusive. This ranking rule does not demonstrate a graph advantage. Masking changes 12/40 issues. All 480 rows reproduce identically except measured latency.

## Outputs

`results/per_instance.csv` records every issue/condition/method/seed, full candidate rankings, metrics, timing and commit. `summary.csv`, `paired_comparisons.csv`, `by_repo.csv`, `by_num_gold.csv`, `by_coverage.csv`, `leakage_summary.json`, `rank_changes.json`, `offline_times.csv` and plots derive from those rows and audit metadata. `experiment_config.json`, `audit.json`, `exclusions.csv` and selection manifests retain provenance and denominators.

Read [the paper](paper/KAGGLE_WRITEUP.md), [research notes](paper/RESEARCH_NOTES.md), [submission checklist](paper/SUBMISSION_CHECKLIST.md), and [literature audit](paper/LITERATURE_AUDIT.md). This is a pilot on a fixed subset, not a claim about all SWE-bench or all graph-assisted agents. Gold patch paths are a proxy for relevant files, not a complete relevance annotation. No Gemma/model run or downstream fix-success result is claimed.

## Data, licenses and release

Original toolkit code is dual licensed: **MIT or Apache-2.0, at your option** (`LICENSE`, `LICENSE-APACHE`). SWE-bench Lite metadata is downloaded from [Hugging Face](https://huggingface.co/datasets/SWE-bench/SWE-bench_Lite), derived from [SWE-bench](https://arxiv.org/abs/2310.06770). The dataset card's license/provenance and individual repository licenses govern third-party data/code; our license does not relicense them. Cached repository code, issue texts and patches are excluded from the release. Derived paths/rankings/commits and short matched masking spans remain for audit; they are not a substitute for upstream licensing. No competition graphs or restricted assets are used.

Public project repository: <https://github.com/sakshamg251206/patchscope-cf> (verified public). No asset is published by installing or evaluating this toolkit. See `paper/COMPETITION_AUDIT.md` for verified requirements and unresolved legal/live-account checks.
