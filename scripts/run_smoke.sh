#!/bin/sh
set -eu
patchscope evaluate --sample 5 --seed 2026 --output "${1:-results/demo}"
patchscope report --results "${1:-results/demo}"
