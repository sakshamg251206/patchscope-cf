#!/bin/sh
set -eu
# Results are immutable; pass a fresh directory to reproduce without overwriting.
patchscope evaluate --sample 40 --seed 2026 --manifest data/selection_manifest.json --output "${1:-results/reproduction}"
patchscope report --results "${1:-results/reproduction}"
