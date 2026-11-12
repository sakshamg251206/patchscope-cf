"""Paired Hit@k differences across the returned-file budget, with bootstrap intervals.

The main report fixes k at 1/5/10. The budget curve suggests the sign of the graph
effect depends on how many files the agent is allowed to open, so this script tests that
directly: for every k it recomputes Hit@k from the saved rankings and bootstraps the
paired real-minus-control difference over issues (rewiring seeds averaged within an
issue first, exactly as in the main report).

Usage: python scripts/budget_analysis.py [results/full300]
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from patchscope.evaluate import paired_bootstrap, write_csv

BUDGETS = (1, 3, 5, 10, 20, 50, 100)
METHODS = ('bm25', 'real', 'rewired', 'edge_drop')


def hit_at_k(rows: list[dict], k: int) -> float:
    """Issue-level mean of the within-issue mean hit, matching report.summarize."""
    return float(np.mean([bool(set(json.loads(r['gold_paths']))
                               & set(json.loads(r['predicted_paths'])[:k])) for r in rows]))


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'results/full300')
    rows = list(csv.DictReader((root / 'per_instance.csv').open()))
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row['condition'], row['method'], row['instance_id'])].append(row)

    table = []
    for condition in sorted({r['condition'] for r in rows}):
        issues = sorted({r['instance_id'] for r in rows if r['condition'] == condition})
        for k in BUDGETS:
            scores = {method: [np.mean([hit_at_k([r], k) for r in grouped[(condition, method, i)]])
                               for i in issues] for method in METHODS}
            for control in ('bm25', 'rewired'):
                table.append(dict(condition=condition, k=k, control=control,
                                  real_hit=float(np.mean(scores['real'])) * 100,
                                  control_hit=float(np.mean(scores[control])) * 100,
                                  **paired_bootstrap(scores['real'], scores[control])))
    write_csv(root / 'budget_comparisons.csv', table)
    print(f'{"cond":7}{"k":>5}{"control":>10}{"real%":>9}{"ctrl%":>9}{"diff_pp":>10}{"95% CI":>20}')
    for r in table:
        interval = '[{:.1f}, {:.1f}]'.format(r['lower_pp'], r['upper_pp'])
        print(f'{r["condition"]:7}{r["k"]:>5}{r["control"]:>10}{r["real_hit"]:>9.1f}'
              f'{r["control_hit"]:>9.1f}{r["difference_pp"]:>10.1f}{interval:>20}')
    print(f'\nwrote {root / "budget_comparisons.csv"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
