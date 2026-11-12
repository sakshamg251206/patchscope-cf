#!/bin/sh
# One-command reproduction of every number in the paper.
#
#   sh scripts/reproduce_all.sh [OUTPUT_DIR]
#
# Default OUTPUT_DIR is results/full300_repro, because result directories are immutable
# and the shipped results/full300 must not be overwritten. Expect roughly 45 minutes on
# a cold cache (almost all of it fetching historical git objects) and under two minutes
# once snapshots are cached. CPU only; no model, GPU or API key is involved.
set -eu
out="${1:-results/full300_repro}"

echo "== unit tests =="
pytest -q

echo "== full SWE-bench Lite test split (300 issues) -> $out =="
patchscope evaluate --sample 300 --seed 2026 --split test \
  --manifest data/selection_manifest_full300.json --output "$out"
patchscope report --results "$out"

echo "== budget analysis and figures =="
python scripts/budget_analysis.py "$out"
python scripts/make_figures.py "$out"

echo "== independent verification of the saved artifacts =="
python scripts/verify_results.py "$out"

echo "== dev-split-only sensitivity sweep (never used to tune the test run) =="
python scripts/dev_sensitivity.py --output "$out/../dev_sensitivity_repro"

echo "== paper table consistency =="
python scripts/check_paper.py paper/KAGGLE_WRITEUP.md "$out"

echo "done: $out"
