# PatchScope-CF — final submission steps

Everything in this file was checked against the live Kaggle competition service on
2026-11-12. The three pages quoted below are `Submission Requirements`, `Evaluation`
and `rules` as returned by Kaggle's own page service for competition id `163111`.

**No Kaggle account action has been performed by the assistant.** Joining, accepting
rules, creating the Writeup and clicking **Submit** are yours to do.

---

## 0. Deadline

| | |
|---|---|
| Final submission deadline | **2026-11-12, 23:59 UTC** |
| Same instant in IST | **2026-11-13, 05:29 IST** |
| Start the manual steps no later than | **22:30 UTC / 04:00 IST** |

Kaggle's own record: `"deadline": "2026-11-12T23:59:00.807Z"`. A **saved draft is not a
submission** — the requirements page states that "Any un-submitted or draft Writeups by
the competition deadline will not be considered by the Judges."

## 1. What the competition requires

From the official **Submission Requirements** page, a valid submission must contain a
Kaggle Writeup with:

1. Title and subtitle
2. Abstract
3. Introduction
4. Description of the research, including methods and experiments
5. Related works and citations

Scope: **3,000 words maximum**, original and unpublished. Optional extras: a public
notebook, and/or an arXiv-ready PDF via the Public Project Link field.

Scoring (**Evaluation** page): Novelty, Quality, Relevance, Verifiability, Clarity —
each 0–5, final score is the plain average. Prizes: Overall Best Paper $15,000,
**Best New Resource $10,000**, Best New Application $10,000.

Limits (**rules** page): max 5 submissions per day, up to 2 final submissions selected
for judging, max team size 5, identity verification required.

## 2. Our submission assets

| Field | Value |
|---|---|
| Title | `PatchScope-CF: Do Code Graphs Really Help Locate Bugs?` |
| Subtitle | `A counterfactual, leakage-audited benchmark for repository-level issue localization` |
| Writeup body | `paper/KAGGLE_WRITEUP.md` — paste as-is (Markdown) |
| Public project link | <https://github.com/sakshamg251206/patchscope-cf> |
| PDF (optional) | `paper/patchscope_cf.pdf` |
| Figures | `results/full300/figures/accuracy_vs_budget.png`, `results/full300/figures/paired_hit5.png`, `results/dev_sensitivity/dev_sensitivity.png` |

## 3. Manual steps, in order

1. Open <https://www.kaggle.com/competitions/gemma-4-developer-agent-paper>.
   Confirm the deadline shown on the live page still matches section 0.
2. Read the **Rules** tab and click **Join Hackathon** / accept the rules. You cannot
   submit without this, and identity verification is required for prize eligibility.
3. Confirm the GitHub repository opens in a logged-out (incognito) window.
4. **Writeups → New Writeup.**
   - Paste the title and subtitle from section 2.
   - Paste the body of `paper/KAGGLE_WRITEUP.md`.
   - Re-upload the three figures through Kaggle's image button. The Markdown file
     references repository-relative paths that will not resolve inside Kaggle.
   - Put the GitHub URL in the **Public Project Link** field (or attach the PDF there).
5. **Save**, then read the rendered page end to end once.
6. Click **Submit** (top right). Confirm the state reads as submitted, not draft.
7. Keep a screenshot of the submitted state.

## 4. Before you click Submit — honest-claims checklist

- [ ] Every number in the Writeup matches `results/full300/summary.csv` and
      `results/full300/paired_comparisons.csv`. Nothing is copied from a smoke run.
- [ ] The Writeup does **not** claim: that Gemma or any language model was run; any
      downstream patch-repair result; state of the art; priority for graph-based
      localization, counterfactual evaluation, query masking, or leakage auditing.
- [ ] The negative/inconclusive findings are still stated as negative and inconclusive.
- [ ] AI assistance is disclosed, and **you** have read the evidence and can defend it.
- [ ] Word count is under 3,000 (`scripts/verify_results.py` prints it).

## 5. Licensing

- Original PatchScope-CF code is released under **MIT or Apache-2.0, at your option**
  (`LICENSE`, `LICENSE-APACHE`). Rule 2.5 requires a winning submission to be licensed
  under an OSI-approved licence that does not limit commercial use, and names Apache 2.0
  as the winner licence type; the dual licence satisfies both readings with no further
  action if the entry wins.
- SWE-bench Lite metadata is downloaded at a pinned Hugging Face revision and is **not**
  redistributed here. Repository source, issue texts and patches stay in the ignored
  local cache; only derived paths, rankings, commit hashes and short masking spans are
  published. Upstream repository licences are unaffected by ours.

## 6. What is deliberately not claimed

PatchScope-CF measures file-level retrieval, not patch correctness. It uses no model, no
embeddings and no GPU. The import graph is static and incomplete. The counterfactual
controls bound one specific question — whether real import topology outranks a
degree-matched null inside a fixed candidate pool — and nothing beyond it.
