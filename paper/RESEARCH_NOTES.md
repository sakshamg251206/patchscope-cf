# Research notes

## Request and protocol

The user supplied `docs/PROJECT_SPEC.md` and authorized implementing/running it autonomously. Workspace was initially empty, not a git repository. Work began 2026-11-12 at approximately 14:05 UTC (19:35 IST). Stated deadline: 23:59 UTC / November 13 05:29 IST; manual reserve begins 22:29 UTC / 03:59 IST.

Research question: whether issue-conditioned static import-graph reranking adds value beyond BM25 and a same-degree graph control, particularly after target-name removal. This is a reusable evaluation resource and a pilot, not a new graph-localization concept or an LLM-agent comparison.

Parameters were chosen before viewing test scores: fixed identical lexical top-100 pools, top-20 seeds, normalized lexical plus 0.5 times one-hop outgoing import transfer; rewiring seeds 2026/2027/2028, five swaps per edge; edge-drop seed 2026; 2,000 paired bootstrap replicates. No parameter was tuned on smoke or test scores. Fixed pools deliberately remove expansion/pool-composition confounding at the cost of blocking discovery beyond BM25 top100. Query/label masking is explicitly diagnostic and label-informed.

`data/selection_manifest.json` freezes the first 40 of all 300 sorted/shuffled test IDs at HF revision b0dde1093fe417d83b7184254edf8199c1f0dff5, seed 2026. It spans seven repositories before exclusions. No replacements. The five smoke issues are the prefix of this fixed test cohort, used for engineering validation and disclosed as such, not an untouched independent holdout. The 23 dev issues span six entirely different repositories; no dev-based hyperparameter search was conducted.

## Implementation and real execution log

- Python 3.12.4 available through uv; initial shell `python3` was 3.14.4. macOS arm64; approximately 67 GiB free at start. git 2.50.1. CPU-only.
- Initial tests failed because modules did not yet exist; implemented labels, immutable selection, read-only git snapshots, then core retrieval and evaluator/report modules in test-first batches.
- Git snapshots are bare repositories fetching only requested commits at depth1. Source blobs read with `git cat-file --batch`; no checkout, setup or test execution of upstream projects. Every filtered gold label must be present at base; new/renamed absent paths cause case exclusion.
- Initial HTTPS download failed because Python's default OpenSSL certificate file was absent. Added certifi and retained verified TLS; no insecure SSL workaround.
- Ranking fixture initially expected a reorder where two scores tied. Hand calculation confirmed deterministic alphabetical tie-break was correct; fixture changed from 2.0 to 2.1 to test actual score movement.
- First actual case: scikit-learn__scikit-learn-12471 at 02dc9ed680e7f53f1b0d410dcdd37341c7958eb1. 249 source files, 1,027 directed edges, no AST failures. Gold sklearn/preprocessing/_encoders.py was BM25 rank1. Actual output recorded during session.
- First five-case smoke run: 5 eligible, no exclusions. Real-graph Hit@5 was lower than lexical. No ranking parameter changed in response.
- Engineering inspection identified missing absolute-import resolution for `lib/` and `src/` layouts. Regression test failed first; added prefix recognition, all tests passed. Corrected smoke rerun in `results/smoke_fixed/`, preserving original `results/smoke/`. This is a correctness fix, not performance tuning. All requested swaps completed in corrected smoke; every degree invariant held.
- Full test and dev execution started only after corrected smoke. Exact timestamps, versions and exclusions are in each run's `experiment_config.json`, `exclusions.csv`, `audit.json` and log.
- Old Python source emits harmless SyntaxWarnings while parsed under Python3.12. These are retained in logs; source is parsed, never executed. Parse errors retain path/module text and are counted.

## Deliberately omitted

No Gemma/LLM arm, competition embeddings, adaptive reranking, model training, downstream repair test, or large hyperparameter search. No claim of first counterfactual or leakage-aware evaluation: Bellam already has placebos/masking, ARB audits leakage and snapshots, LocAgent has graph ablations. Details in `LITERATURE_AUDIT.md`.

## Reproduction and limits

Runtime is a warm per-query microbenchmark, not end-to-end clone latency. Common lexical work is measured once and charged identically to every method. Snapshot loading, AST/BM25 build and graph perturbation time are separate. An issue bootstrap ignores repository clustering and is descriptive. Rewiring preserves degree exactly but is not proved to mix uniformly. Labels are changed source files rather than exhaustive relevance; test-only/new-file cases can be excluded by design. No representative-all-Lite or state-of-the-art claim is supported.

## Submission provenance

Official indexed requirements verified by a separate source audit; live rules body could not be retrieved. Deadline and Save→Submit workflow confirmed. No Kaggle account state or public repository link exists in this artifact; no publication/submission took place. Human must check rules, authorship, data licenses and final evidence before submitting. AI assistance was used in implementation, testing, analysis and draft writing; the entrant must review and take responsibility for the paper.

## Independent review and corrected runs

Independent code review found module-name masking missed `lib/`/`src/` canonical names and package-initializer dotted modules (affecting Sphinx cases 8282 and 8595). Added failing regression tests then shared the index's module naming rule with masking. Also fixed a diff parser edge case where an added line beginning `+++ b/...` inside a hunk could be misread as a header (no selected case had this pattern), verified cache source checksums on reuse, pinned the downloader revision even for fresh caches, and rejected duplicate control seeds or mismatched raw/masked cohorts in reports. Nineteen tests passed after fixes. Ranking parameters were unchanged.

Preserved original complete test outputs under `results/pre_review/` and dev under `results/dev_pre_review/`. Corrected final test outputs are at `results/`; corrected dev at `results/dev/`. Smoke outputs are engineering history, not extra independent evidence. Both corrected runs started from the same immutable selection and base-commit source cache; checksums were verified. Source-module hashes are recorded in corrected configs.

## Final measured outcome and verification

Corrected main run: 2026-11-12T14:18:44.626527+00:00 through 14:19:32.001930+00:00. All 40 selected test issues were eligible across seven repositories; zero exclusions. Every case has one gold source file. Raw Hit@5: BM25 65.0%, real 47.5%, rewired mean 50.8%, edge deletion 50.0%. Real−BM25 −17.5 pp [−32.5, −2.5]; real−rewired −3.3 pp [−12.5, +5.0]. Masked Hit@5: 65.0%, 45.0%, 50.0%, 47.5%, respectively. Twelve issues/34 spans changed. No graph advantage is demonstrated at this budget; the plot shows different behavior at larger k, so claims remain budget-specific.

Corrected dev: 23 eligible, six repositories, zero exclusions. Main and dev are separate, not pooled. Per-case source/AST caps caused file exclusions (recorded individually) but no issue exclusions. Fifteen AST failures occur in one old Requests snapshot's vendored code; path/module lexical text remains. All test gold nodes have nonzero import degree; a zero-degree subgroup would be empty. No case was removed for poor performance.

A final cache-limit validation regression increased the suite to 20 tests. It did not change retrieval. The main config's data.py hash predates this last guard; `results/reproduction/experiment_config.json` records final source hashes. The full README reproduction command ran again under the final code: all 480 rows were **identical excluding measured query latency**, and all reproduction source-module hashes match current files. This independently checks unchanged results after the guard rather than rewriting the main config's historical provenance.

Passed: `uv sync --locked --extra test`; `uv run --locked pytest -q` (20); local `examples/demo.py`; real README five-case evaluate/report; full 40-case reproduction evaluate/report; `scripts/verify_results.py results` and `results/reproduction`; compileall; numeric paper-table consistency check. Word count of initial final draft: 2,161 whitespace-separated words, abstract 181. Both actual figure files were visually inspected. Source and report reviews are recorded in `CODE_REVIEW.md`.

Remaining limits: no external publication, account eligibility/rule acceptance/submission, cold-download benchmark, null-mixing proof, repository-cluster inference, broad systematic priority claim, model arm or downstream repair. The human submission checklist remains necessary.

## Clean-release installation check

A fresh extracted archive initially selected host Python3.14 through uv; pinned PyArrow19.0.1 has no compatible wheel and its source build failed for absent Arrow C++ libraries. The benchmark environment itself remained Python3.12.4 and its tests/results were unaffected. Added `.python-version` selecting 3.12, so the documented `uv sync --locked --extra test` chooses the measured interpreter on a clean machine. The successful in-workspace install alone would not have caught this portability issue. The final release archive includes `.python-version` and `.gitignore`.

Final clean extracted-archive check passed `uv sync --locked --extra test`, all20tests, and `examples/demo.py` with Python3.12.4. Release bundle includes final reviewed code, ignored-cache rules, interpreter pin, main/dev artifacts and figures, without upstream source caches. See `results/verification.json`.
