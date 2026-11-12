# CODEX MASTER PROMPT — PATCHSCOPE-CF

You are my autonomous senior research engineer, software engineer, experimental scientist, and technical writer. **Implement and run** a complete, credible, reproducible research artifact for the Google DeepMind / Kaggle "Gemma 4 Developer Agent Paper Track": https://www.kaggle.com/competitions/gemma-4-developer-agent-paper . Do not stop at a design, TODO list, or skeleton. Build, test, benchmark, inspect the outputs, and prepare the final Kaggle Writeup. Ask me only for an action requiring my account/login/permission or information you cannot obtain; otherwise choose defensible defaults and proceed. Never claim an experiment ran unless it actually ran. Never invent benchmarks, citations, numbers, model comparisons, links, or performance gains.

## 0. Deadline and competition constraints (non-negotiable)

- Paper deadline: **2026-11-12 23:59 UTC = 2026-11-13 05:29 IST**. Check actual current time. Preserve **at least 90 minutes** before the deadline for manual submission, uploading or linking assets, and fixing formatting. If there is insufficient time, reduce scope aggressively but deliver a real tested benchmark and finished paper.
- Separate **paper track**, not the Gemma 4 patch-generation leaderboard. The paper track requires joining the competition and **submitting a Kaggle Writeup**; a draft does not count. No `submission.zip`/leaderboard agent config is required for the paper-track submission.
- Paper length **maximum 3,000 words**. Required: title, subtitle, abstract, introduction, research methods and experiments, related work and citations. Optional: public Kaggle Notebook, public accessible project link, PDF.
- Target: **Best New Resource ($10,000)**, with relevance to overall Best Paper. The five official criteria are novelty, quality, relevance, verifiability, clarity (equal weight). A novel resource means actual reusable code/benchmark, not a concept paper.
- Gemma 4 use is not strictly required for this separate paper track; do not falsely claim to have run Gemma. If the competition's released graphs/embeddings are accessible and permit use, add a clearly labelled optional adapter/evaluation; prioritize completed real experiments first. If using competition assets, comply with permissions and redistribution restrictions.
- Read the latest competition overview/rules and the submission instructions before writing final deliverables; report any discrepancies. Relevant official page: https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/overview/submission-requirements .

## 1. Project identity and scientific question

Project title: **PatchScope-CF: Do Code Graphs Really Help Locate Bugs? A Counterfactual, Leakage-Audited Benchmark**.

Thesis/question (not assumed true): Static code graphs are often added to coding-agent retrieval, but observed gains may be caused by lexical overlap, node popularity, or larger candidate pools. Does an issue-conditioned graph reranker improve localization **beyond** a lexical baseline and a *degree-preserving rewired graph control*, at fixed candidate budgets, particularly when the issue text does not explicitly name the target file?

Make TWO contributions:
1. **Reusable benchmark toolkit/resource** for real-world issue-to-code file localization at frozen pre-fix commits, including reproducible gold-label extraction, issue leakage audit, robust controls, fair evaluation metrics and a simple CLI.
2. **Controlled empirical audit** comparing lexical retrieval, real graph expansion, randomly rewired graph expansion, and graph ablations. Report positive, null, and negative results truthfully, including cases where real graphs make retrieval worse.

This must NOT be positioned as inventing graph-based localization. Prior work exists (SWE-bench; LocAgent; recent 2026 agent-retrieval research). The differentiator is the **counterfactual intervention and leakage-aware, budget-matched evaluation packaged as a reproducible lightweight resource**. Check adjacent literature to avoid claiming novelty already established elsewhere.

## 2. Research data, provenance, and correct scope

Primary source: **SWE-bench Lite**, real issue/PR pairs: https://huggingface.co/datasets/SWE-bench/SWE-bench_Lite . Includes `instance_id`, `repo`, `base_commit`, `problem_statement`, `patch`, `test_patch`. Official SWE-bench research: https://arxiv.org/abs/2310.06770 .

- Prefer `dev` split only for hyperparameter selection and a **precommitted deterministic test subset** from `test` (seed 2026) for final evaluation. If dev is too small or lacks repos, describe this limitation. Target >=40 valid test issues spanning >=2 repos; if resource constraints prevent this, run as many verifiably possible and state precise number, selection and exclusions. **Never imply a small convenience sample represents all SWE-bench Lite.**
- For each instance, use its exact `base_commit`; the retrieval index MUST be built from the repository snapshot **before the gold patch**, not from the fixed version. Avoid leakage through file content, patch metadata, test patches or gold labels. Gold patches are used ONLY to derive evaluation labels after selection, NEVER to score/rank candidate files.
- Compute gold source file paths from unified diff `+++ b/...` (handle `/dev/null`, renames, Windows paths defensively). Exclude tests/docs/generated/config files with documented reproducible rules; require gold path(s) to be present at `base_commit` for the primary file-localization metric. If a patch contains only new files or all labels unavailable, exclude with documented reason; do not silently drop failures.
- Do not download/re-distribute giant repositories as artifacts. Keep a local cache under `data/cache/` ignored by git. Store only the minimal derived per-instance metadata and generated results; prefer script-driven re-download for data license and size safety. Document data/third-party license and source citations; license only our original code (MIT or Apache 2.0 if legally appropriate).
- Reuse git clones per repository. Index each needed base snapshot; cache keyed by repo and commit. Limit maximum file size, files examined, memory and checkout time. Handle network errors with retries and explicit logged exclusions. Never run untrusted project setup scripts. `git` commands should operate only inside a separate cache directory, never overwrite the user's existing workspace.
- Give transparent split manifest `data/selection_manifest.json` with IDs, repos, commits, seed, inclusion/exclusion reasons, dataset revision/commit if available. Freeze selection before looking at final test performance. Never cherry-pick results.

## 3. Core implementation architecture

Use Python 3.11+ and a small dependency set: `datasets` or HF parquet HTTP fallback, `rank-bm25` (or own tested BM25), `networkx`, `numpy`, `pandas`, `matplotlib`, `pytest`, `tqdm` as needed. Keep CPU-only; no GPU or paid API requirement. Provide a `pyproject.toml`, lock/pinned versions if practical, README and deterministic CLI.

Suggested tree (adapt if useful):

```
patchscope-cf/
  README.md
  LICENSE
  pyproject.toml
  .gitignore
  patchscope/
    __init__.py
    cli.py
    data.py            # downloads + frozen commits + inclusion/exclusion audit
    labels.py          # unified diff -> source-file gold labels
    index.py           # Python AST file/symbol indexing
    graph.py           # directed static structural graph + rewired controls
    retrieve.py        # lexical, graph variants, budget matching
    masking.py         # leakage audit, raw/masked issue variants
    evaluate.py        # metrics + paired control comparisons + CI
    report.py          # tables + plots + markdown export
    util.py
  tests/
  scripts/
    run_smoke.sh
    run_experiments.sh
  data/
    selection_manifest.json
  results/
    per_instance.csv
    summary.csv
    experiment_config.json
    exclusions.csv
    figures/
  paper/
    KAGGLE_WRITEUP.md
    SUBMISSION_CHECKLIST.md
    RESEARCH_NOTES.md
  examples/
    demo.py
```

### 3A. Retrieval index

- For each eligible Python source `.py` file, extract path tokens (split snake/camel names), module name, AST class/function/method names, import names and docstrings. Optionally short source snippets under fixed character/token caps. Record exact index text construction; never use anything from gold patch in index.
- Build a **file-level directed graph** from resolvable intra-repository `import/from import` relationships and, if reliable, simple AST `call` references. Preserve edge types and confidence; static resolution is incomplete, so do not claim this is a complete call graph. Eliminate external unresolved targets. Consider edges from importer to imported module. Unit-test resolution rules.
- Make a stable reproducible tokenizer (lowercase, delimiters, camel split, stopword policy) shared by all comparisons. Build BM25 on exactly the same index text for all variants.
- For each issue query, BM25 produces initial top M files. Graph reranking uses only graph edges and top-M seed scores; e.g. 1-hop expansion with decaying weight. Final output returns top-k FILES, with candidate budget matched across methods and deterministic tie handling.
- Implement **real graph**, **graph-off BM25 baseline**, **degree-preserving directed edge-swap control** (try a bounded series of valid swaps preserving in/out degree, avoid duplicates/self-loops), and **50% edge-deleted graph** control. Use >=3 independent rewiring seeds if feasible; report if sparsity prevents swaps and use a clearly labelled weaker control only if necessary. The **rewired graph control must pass degree-preservation tests**.
- Optional: adaptive/uncertainty-gated graph expansion (e.g., based on top-2 BM25 margin or entropy), tuned ONLY on dev and compared against fixed graph expansion under matched budget. Never make it the central claim unless tested.

### 3B. Leakage and counterfactual conditions

Create two clearly defined evaluation conditions:
1. **Raw issue**: original `problem_statement`, excluding `hints_text` and future patch details.
2. **Target-name masked issue**: remove explicit mentions of the gold file path, module dotted path and unambiguous target basename (where they occur). This is a diagnostic **label-informed stress-test** with information removal, not an ordinary deployment setting; only the evaluation query is masked, never indexed code. Report masking frequency and impact. Avoid broad deletion of common words: use guarded patterns and record before/after changed spans. Include an audit showing counts of issues whose descriptions mention target paths/names.

Do not call masking causal by itself. The true graph intervention is the **real vs rewired graph** comparison with identical query, seed candidates, graph size, ranking formula and top-k budget.

### 3C. Evaluation metrics and rigor

Primary metrics:
- **Hit@1, Hit@5, Hit@10**: fraction of instances where at least ONE gold source file is in the first k results.
- **MRR@10**: reciprocal rank of the first gold hit, zero when no hit in first ten.
- **Gold-file Recall@k**: number of gold files in top k divided by total gold files, averaged across instances.
- **Runtime per query** (median, P95) AND offline index construction time; do not mix them.

Run same eligible instances and identical code snapshot for every retrieval variant. Preserve per-case CSV rows with `instance_id, repo, method, condition, seed, num_files, num_edges, num_gold, gold_paths, predicted_paths, hit1, hit5, hit10, mrr10, recall5, query_ms`, plus source provenance. The test cohort must not vary by method. Do not silently replace missing results with success.

Compute paired differences (real graph minus BM25; real graph minus rewired graph mean) in percentage points; if enough samples, include 95% paired bootstrap CI (>=1000 replicates, seed fixed). If CIs overlap zero, say inconclusive; never claim significance solely because one score is larger. Break out failure cases and sensitivity by repo, raw vs masked, number of gold files, and graph edge coverage if sample sizes permit. Draw an accuracy-vs-budget plot. Include one specific inspectable positive and one negative case with issue ID, predicted paths and measured ranks, without exposing test-derived labels inside retrieval logic.

**Mandatory sanity checks**: BM25-only is identical regardless of graph variants; rewired graph retains node set and each node's in-degree/out-degree; every ranked path exists at the pre-fix snapshot; deterministic run with same seed yields same outputs; label extractor matches fixture patches; masked text cannot accidentally contain a full target path if the matcher says masked; no future test_patch/solution data in indexing; same test cohort and top-k for all methods.

## 4. Experiment execution order (work in this order; do not skip to the paper)

1. Inspect environment: Python, git, disk space, available network, Kaggle/HF access, current UTC time. Check official competition rules. Record actual constraints and time remaining.
2. Create a working repo and minimal functioning CLI plus unit tests. If `git` repo is absent, initialize project locally, but do not assume GitHub credentials or publish without permission.
3. Fetch SWE-bench Lite metadata, freeze a manifest, download/checkout at least one real repo snapshot, extract labels, index and rank an actual issue. Print real top-10 files and gold paths to verify the pipeline.
4. Implement BM25, real graph, rewired control, edge-drop control and issue masking. Unit-test degree preservation, caching and label leakage.
5. Run a smoke evaluation of >=5 real issues first. Inspect for suspicious perfect scores, filename leakage or wrong commit/version. Repair any bugs.
6. Run a dev/held-out experiment (ideally >=40 test issues, >=2 repos) and save machine-readable configs/results. Never tune parameters on test. Record full denominator and exclusions.
7. Generate charts, research note, failure analysis and final report **from actual CSV/JSON**, not synthetic example figures.
8. Produce the final polished Kaggle Writeup under 3,000 words with exact measurements and substantiated citations. If results are poor or dataset is small, frame it as an auditable counterfactual evaluation resource and a pilot study, NOT as state-of-the-art.
9. Produce a public notebook-compatible example in `examples/` or `notebooks/` if feasible. It should run a small demonstration without huge downloads or credentials. Test notebook cells if practical.
10. Prepare clean files for public release and a submission checklist. If GitHub/Kaggle login is available, **ask for explicit permission before any external publication/submission**. Otherwise output exact instructions and file paths for me.

### Priority when deadline is tight

**P0 (must finish)**: valid joined paper track (human step), runnable CLI, verifiable original contribution, actual metrics over real instances, writeup under 3k, final manual Kaggle submission.
**P1**: graph rewiring, multiple repos, paired CI, downloadable plots, clean README.
**P2**: optional Gemma comparison or import of competition-provided embeddings, richer notebook/demo, advanced hyperparameter optimization.

If a dependency or large clone stalls, immediately simplify to a smaller valid fixed cohort and document the limitation. Do **not** burn all the remaining time on a large-scale benchmark at the cost of having no submitted Writeup.

## 5. Paper and public presentation requirements

Write `paper/KAGGLE_WRITEUP.md` with this structure (use measured claims only):

- **Title**: PatchScope-CF: Do Code Graphs Really Help Locate Bugs?
- **Subtitle**: A counterfactual, leakage-audited benchmark for repository-level issue localization.
- **Abstract** (~170–220 words): research question, method, sample, actual results, contribution/limitations.
- **1. Motivation / Introduction**: bug localization bottleneck; why graph gains need a stronger control.
- **2. Contributions / Resource**: deterministic CLI, instance provenance, gold-label rules, graph perturbations, leakage masking and benchmark manifest.
- **3. Data and Protocol**: SWE-bench Lite version, dev/test cohort selection, actual repo count, pre-fix commits, inclusion/exclusion, metric definitions, query conditions, exact graph construction and budgets.
- **4. Methods**: BM25 baseline; real graph; rewired same-degree graph; edge-drop control; optional adaptive variant.
- **5. Results**: table including n, Hit@1/5/10, MRR@10, time; paired differences and CIs where justified, chart, examples.
- **6. Failure Analysis / Limitations**: AST incompleteness, gold-patch label proxy, limited repos, masking artifacts, optional model-free evaluation (do not imply downstream fix success).
- **7. Related Work**: cite SWE-bench, LocAgent and recent retrieval research properly; state what is and is not new.
- **8. Reproducibility**: command snippets, seeds, Python version, hardware, dependencies, data and code links once actually published.
- **9. Conclusion**: empirical answer calibrated to the results.
- **References** with verifiable URLs and bibliographic details.

Check these concrete references and add only if verified:
- Jimenez et al., SWE-bench: https://arxiv.org/abs/2310.06770
- LocAgent (ACL 2025): https://aclanthology.org/2025.acl-long.426/
- Agent Retrieval Bench (2026): https://arxiv.org/abs/2607.24882
- How Do Small Coding Agents Use Code Graphs and Embeddings? (2026): https://arxiv.org/abs/2610.33958
- Code Retrieval Representations in Agentic Bug Localization (2026): https://arxiv.org/abs/2607.11046

Do not plagiarize, copy text, misattribute or claim priority over existing work. Ensure bibliography entries actually exist. State any material AI assistance if required by competition rules.

Also write:
- `README.md` with a compelling one-paragraph pitch, one-minute installation/demo, exact reproduction, scope and limitations.
- `paper/SUBMISSION_CHECKLIST.md` with real status and manual steps: Join Hackathon > Writeups > New Writeup > paste final contents > add public project links/notebook if ready > Save > **Submit** > verify confirmed submitted status. Include exact deadline in UTC and IST.
- `paper/RESEARCH_NOTES.md` with decisions, data exclusions, attempted ideas that failed, real experiment logs and exact timestamp of execution.
- `results/summary.csv`, `results/per_instance.csv`, `results/experiment_config.json`, `results/exclusions.csv` and figures generated from actual runs.
- Provide a simple terminal demo, e.g. `patchscope evaluate --sample 5 --seed 2026`, using whichever CLI interface you implement. README commands must be run successfully.

## 6. Definition of DONE — verify everything

Before you report success:
- [ ] `pytest -q` passes, or any failures are explicitly listed and resolved if possible.
- [ ] The README install and smoke commands actually run.
- [ ] There is at least one *real* frozen-commit issue evaluation; ideally a reasonably sized held-out cohort.
- [ ] File gold labels are correct on checked fixture and real cases; no gold patch in retrieval index.
- [ ] All four methods ran on same instances; graph swap truly preserves in/out degrees.
- [ ] Every numeric paper claim exists in `results/` with clear denominator.
- [ ] The claims section plainly says whether real graph beats rewired graph/BM25 or not, and discusses uncertainty.
- [ ] `KAGGLE_WRITEUP.md` is <=3000 words (include word count in terminal output); valid title/subtitle/abstract/methods/experiments/related work/citations.
- [ ] Public links are real and accessible or clearly marked "TO BE UPLOADED". Never invent a GitHub or Kaggle URL.
- [ ] A human knows which steps require Kaggle login and that **Save is not Submit**.

At the END of your work, output a concise status report containing:
1. **What was actually built** and tested.
2. **Exact number of eligible benchmark issues/repos** and reasons for exclusions.
3. **The actual results table** and one-sentence conclusion, including null findings.
4. **Exact files** to open or publish (especially `paper/KAGGLE_WRITEUP.md`).
5. **Commands that passed**, plus any known limitations.
6. **The next 3 manual actions for me**, focused on getting the Kaggle Writeup submitted before the deadline.

Start executing immediately. Do not ask me for high-level preferences or stop after planning; make the best defensible choices and build the resource end to end.
