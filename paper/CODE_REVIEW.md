# Independent implementation review

Reviewed `patchscope/*.py`, the four test files, `docs/PROJECT_SPEC.md`, and the implementation plan on 2026-11-12. This review made no code changes. `pytest -q` passed: **14 tests** at review time. Findings below describe the source at review time; the implementation may subsequently fix them.

## Findings requiring correction

### P1 — Diagnostic masking misses package modules, including two selected test issues

**Evidence:** `patchscope/masking.py:13` derives dotted names directly from the repository path, retaining `lib`/`src` and `.__init__`. Actual importable names omit those parts. Reproductions:

- Gold `lib/pkg/abc.py`, query `pkg.abc failure` → unchanged, zero spans.
- Gold `pkg/__init__.py`, query `pkg failure` → unchanged, zero spans.
- In the frozen 40-issue cohort, `sphinx-doc__sphinx-8282` and `sphinx-doc__sphinx-8595` contain `sphinx.ext.autodoc`, corresponding to gold `sphinx/ext/autodoc/__init__.py`; the module name remains in masked queries.

**Impact:** The advertised module-name-removal stress-test is not implemented correctly, and the masking audit undercounts changes. Raw results are unaffected. **Minimal fix:** share the index's module-name normalization, strip package initializer suffixes, and test both layouts and package initializers. Keep guards on bare common words. Rerun the same frozen cohort and preserve superseded runs; this is a correctness repair, not parameter tuning.

### P2 — Unified-diff label extraction mistakes added source text for a file header

**Evidence:** `patchscope/labels.py:19–21` accepts every line beginning `+++ `. In a diff hunk, added source text beginning `++ b/pkg/fake.py` is serialized as `+++ b/pkg/fake.py`. A fixture containing a genuine `+++ b/pkg/a.py` header and that added line returns **both** paths as gold.

**Impact:** General toolkit inputs can produce false labels or exclusions. I checked selected cohort patches and found no such hunk lines, so there is no demonstrated corruption of the current test labels. **Minimal fix:** track diff file-header/hunk state rather than matching prefixes globally; add a regression fixture. Also test Git-quoted paths separately from shell quoting because Git uses C-style escapes.

### P2 — Snapshot cache contents are trusted without checking the recorded source hash

**Evidence:** `patchscope/data.py:85–89` checks only `audit.commit`, then returns cached files. A JSON cache with the requested commit, `source_sha256='wrong'`, and `{'future.py': 'future solution'}` is accepted.

**Impact:** Silent cache corruption or accidental edits can invalidate the pre-fix-content guarantee while provenance still claims the original commit. No current cache corruption was observed. **Minimal fix:** recompute and verify the saved source SHA-256, repo identity, schema and indexing limits on cache load; reject/rebuild mismatches. Add a tampered-cache test. A checksum catches accidental edits, not malicious rewriting of both payload and hash.

### P2 — Fresh-cache reproduction follows the latest dataset revision

**Evidence:** `patchscope/data.py:48–50` requests the unversioned dataset API and takes its current SHA. The selected revision is recorded, but there is no argument/default allowing a clean reproduction to choose that revision. A future dataset update can change the input or make the frozen manifest check fail.

**Impact:** Current runs are auditable but the published reproduction command is not fully revision-pinned. **Minimal fix:** pin the released revision by default, or expose an explicit revision option and use the recorded SHA in README reproduction commands.

### P2 — Report validation accepts duplicate seed records and different condition cohorts

**Evidence:** `patchscope/report.py:25–32` validates row counts, not seed identities, and compares methods only within each condition. A fixture with rewired seed 2026 repeated three times and entirely different issue IDs in raw versus masked conditions is accepted by `summarize`.

**Impact:** The current evaluator emits the intended seed/cohort structure, but malformed or concatenated CSVs can generate apparently paired reports without triggering the advertised guard. **Minimal fix:** validate unique `(instance, condition, method, seed)` keys, exact expected seed sets from config, and identical raw/masked IDs. Also validate metadata and candidate sets across methods when generating the final report.

## Checks that passed inspection

- On cache miss, snapshots resolve the requested full commit and read its Git tree/blobs without checkout or applying any patch; no repository setup scripts execute.
- The AST index and ranking interfaces accept no patch, hints, future test patch, or gold labels. `evaluate_case` uses `problem_statement`; gold enters only metrics and diagnostic masking.
- Existing import fixtures cover relative imports, package initializers and `src`/`lib` layouts. Syntax failures are recorded and retain path/module lexical content.
- Directed swaps preserve node sets and each node's exact in/out degree, avoid introducing loops/duplicate edges, and record successful swaps and retained-edge fractions.
- Ranking uses an identical lexical candidate pool and top-seed scores for real and rewired arms. The graph-off/alpha-zero identity checks are valid.
- Hit, reciprocal-rank and multi-gold recall calculations are correct. Reports average rewiring seeds within issues before paired bootstrap, avoiding seed pseudo-replication.
- Cohort selection occurs before label extraction/performance; exclusions are logged without replacement; result rows are checkpointed and unfinished runs cannot produce a normal report.

## Scientific limitations, not implementation bugs

- A fixed top-100 lexical pool tests reranking only; graph discovery outside that pool is impossible by design.
- Import edges are incomplete static evidence, not a call graph. Namespaced/dynamic imports and old Python syntax remain limitations.
- Five successful swaps per edge do not prove Markov-chain mixing or uniform sampling. Three random seeds measure only a small portion of null variability.
- The 50% edge-drop arm changes degrees and propagation denominators; interpret it as an ablation, not a degree-matched null.
- Gold-file labels reflect one accepted patch, not every useful file. Requiring all labels present is conservative and can exclude partly-new patches.
- Query masking is label-informed and changes lexical evidence; it is not a deployment transform or stand-alone causal result.
- Issue-level bootstrap intervals do not account for repository clustering or multiplicity across many metrics. Treat pilot comparisons and slices as descriptive.
- Timing is warm, sequential and measured while other work may run; medians/P95 are descriptive hardware-specific observations, not speedup claims.

Skipped external publication, full Git blob-by-blob revalidation of every cached snapshot, and end-to-end experiment reruns. Main immediate risk: masked-condition claims should wait for the module-name fix and same-cohort rerun.

## Final resolution and factual review

A second independent pass reviewed the repaired implementation and final paper. **No release-blocking issue remains for the measured pilot.** Commands rerun during this pass: `pytest -q` (**20 passed**), `python scripts/verify_results.py results` (**40 issues / 7 repositories / 480 rows verified**), and the same verifier for `results/dev` (**23 issues / 6 repositories / 276 rows verified**).

### Resolution of earlier findings

- **Package/source-layout masking:** corrected using the index's canonical module normalization and initializer suffix removal. A regression test covers `lib/pkg/abc.py` and `sphinx/ext/autodoc/__init__.py`. The corrected audit now records `sphinx.ext.autodoc` matches in both previously affected Sphinx cases. Main masked rankings were rerun on the same frozen cohort.
- **Hunk/header confusion:** corrected by tracking unified-diff hunk line counts, with a regression test for header-looking added content. Windows drive paths are rejected. Git C-style escaped filenames remain a general parser limitation; no current cohort trigger was found.
- **Cache integrity/protocol:** cache reuse now checks repository, commit, source checksum and file-limit settings; tampering and incompatible-limit regression tests pass. This is protection against accidental cache corruption, not authentication against an adversary able to rewrite both data and checksum.
- **Dataset revision:** the dataset SHA is now pinned in the downloader and agrees with the frozen manifest and final paper.
- **Report pairing:** duplicate seeds and differing raw/masked cohorts are rejected by reporting tests. The standalone result verifier additionally validates exact expected seed sets, candidate-pool equality, snapshot membership and recomputed metric/summary consistency.

### Paper claims independently checked

The 2,161-word `paper/KAGGLE_WRITEUP.md` is below 3,000 words. Its eight result-table rows agree with `summary.csv`, including rounded MRR and median/P95 query latency. Counts agree with the manifest/audit: 40 distinct commits, seven repositories with the stated 17/6/6/5/3/2/1 allocation, zero exclusions, one gold file per selected case, 12 masked queries and 34 spans. The separate dev Hit@5 values and denominator match its saved results.

I independently recomputed the four reported Hit@5 paired intervals from per-instance rows: raw real-minus-BM25 **−17.5 [−32.5, −2.5]** points; raw real-minus-rewired mean **−3.3 [−12.5, +5.0]**; masked **−20.0 [−35.0, −5.0]** and **−5.0 [−13.3, +3.3]**, respectively. The text correctly calls the graph-versus-rewired comparisons inconclusive and labels intervals descriptive, issue-level, unadjusted and insensitive to repository clustering.

All 120 test rewiring controls completed their requested swaps; median retained-edge fraction is **0.169693**, correctly rounded to **0.170**. The first-gold raw rank movement counts are **10 improved / 24 worsened / 6 unchanged**. The positive Django10924 example is exactly **7→2**, with the stated top two; negative Django12453 is exactly **5→8**, also with the stated top two. The larger-budget caveat is supported: real and BM25 tie at k=20, real is higher at k=50, and they converge at the shared full pool.

Offline medians independently match **816.22 ms AST**, **29.17 ms BM25**, **124.73 ms combined controls**, and **23.84 ms cached snapshot load**. These are clearly separated from warm per-query timings; the paper makes no speedup or cold-download claim. Hardware inspection confirms Apple M2, eight logical CPUs and eight GiB RAM. Fifteen AST failures occur in Requests863 only, and every gold node has nonzero graph degree, as stated.

The current `data.py` hash differs from the main run's recorded source hash because cache-limit validation was added afterward; all other recorded module hashes match. Retaining the historical hash is appropriate. The independent full reproduction uses the current source; its ranking comparison is being performed separately by the primary engineer.

Novelty language is appropriately narrow, cites existing placebo/masking/leakage precedents, and avoids priority, state-of-the-art, downstream-repair and Gemma-execution claims. Smoke overlap with test is disclosed. Publication and account submission are honestly marked unfinished; the local figure link needs upload/replacement in Kaggle as the checklist explains.

Skipped account/legal-rule acceptance, publication/submission and an independent clean-network redownload of every snapshot. Residual risk is scientific scope and human submission readiness, not an observed inconsistency in the final measured claims.
