"""Print every number the paper quotes, straight from the saved result artifacts.

A reader can run this and compare its output line by line with the paper, instead of
trusting prose. It derives nothing new: it only reads the exported CSV/JSON files.

Usage: python scripts/paper_numbers.py [results/full300]
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np


def read_csv(path: Path) -> list[dict]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def section(title: str) -> None:
    print(f'\n### {title}')


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'results/full300')
    config = json.loads((root / 'experiment_config.json').read_text())
    audits = json.loads((root / 'audit.json').read_text())

    section('cohort')
    print(f'requested={config["requested"]} eligible={config["eligible"]} '
          f'excluded={config["excluded"]} repos={len(config["repos"])}')
    print(f'revision={config["revision"]} split={config["split"]} seed={config["seed"]}')
    print(f'alpha={config["alpha"]} pool={config["candidate_budget"]} seeds={config["seed_budget"]} '
          f'rewiring_seeds={config["rewiring_seeds"]} bootstrap={config["bootstrap_replicates"]}')
    per_repo_counts = {}
    for audit in audits:
        per_repo_counts[audit['repo']] = per_repo_counts.get(audit['repo'], 0) + 1
    print('issues per repo: ' + ', '.join(f'{k.split("/")[-1]} {v}'
                                          for k, v in sorted(per_repo_counts.items(), key=lambda kv: -kv[1])))
    print(f'distinct base commits: {len({a["base_commit"] for a in audits})}')
    exclusions = read_csv(root / 'exclusions.csv')
    for row in exclusions:
        print(f'  EXCLUDED {row["instance_id"]}: {row["reason"][:140]}')

    section('gold labels')
    gold_counts: dict[int, int] = {}
    for row in read_csv(root / 'per_instance.csv'):
        if row['condition'] == 'raw' and row['method'] == 'bm25':
            n = int(row['num_gold'])
            gold_counts[n] = gold_counts.get(n, 0) + 1
    print('gold files per issue: ' + ', '.join(f'{k} file(s): {v} issues'
                                               for k, v in sorted(gold_counts.items())))

    section('headline table (summary.csv)')
    for row in read_csv(root / 'summary.csv'):
        print(f'{row["condition"]:7} {row["method"]:10} n={row["n"]:>4} '
              f'hit1={100*float(row["hit1"]):5.1f} hit5={100*float(row["hit5"]):5.1f} '
              f'hit10={100*float(row["hit10"]):5.1f} mrr10={float(row["mrr10"]):.3f} '
              f'recall5={100*float(row["recall5"]):5.1f} '
              f'ms={float(row["query_median_ms"]):.2f}/{float(row["query_p95_ms"]):.2f}')

    section('paired differences, Hit@5 and MRR@10 (paired_comparisons.csv)')
    for row in read_csv(root / 'paired_comparisons.csv'):
        if row['metric'] in ('hit5', 'mrr10'):
            print(f'{row["condition"]:7} real - {row["control"]:10} {row["metric"]:6} '
                  f'{float(row["difference_pp"]):+6.1f} pp  '
                  f'[{float(row["lower_pp"]):+6.1f}, {float(row["upper_pp"]):+6.1f}]  n={row["n"]}')

    budget = root / 'budget_comparisons.csv'
    if budget.exists():
        section('effect versus output budget, raw (budget_comparisons.csv)')
        for row in read_csv(budget):
            if row['condition'] == 'raw':
                print(f'k={int(row["k"]):>3} real - {row["control"]:8} '
                      f'real={float(row["real_hit"]):5.1f} ctrl={float(row["control_hit"]):5.1f} '
                      f'{float(row["difference_pp"]):+6.1f} pp '
                      f'[{float(row["lower_pp"]):+6.1f}, {float(row["upper_pp"]):+6.1f}]')

    section('per repository, raw Hit@5 (by_repo.csv)')
    repo_rows = [r for r in read_csv(root / 'by_repo.csv') if r['condition'] == 'raw']
    repos = sorted({r['repo'] for r in repo_rows},
                   key=lambda name: -int(next(r['n'] for r in repo_rows if r['repo'] == name)))
    worse = 0
    for repo in repos:
        values = {r['method']: 100 * float(r['hit5']) for r in repo_rows if r['repo'] == repo}
        n = next(r['n'] for r in repo_rows if r['repo'] == repo)
        worse += values['real'] < values['bm25']
        print(f'{repo:28} n={n:>4} bm25={values["bm25"]:5.1f} real={values["real"]:5.1f} '
              f'rewired={values["rewired"]:5.1f} edge_drop={values["edge_drop"]:5.1f}')
    print(f'repositories where real < bm25 at Hit@5: {worse}/{len(repos)}')

    section('masking diagnostic (leakage_summary.json)')
    print(json.dumps(json.loads((root / 'leakage_summary.json').read_text()), indent=2))

    section('rank movement, raw, first gold file (rank_changes.json)')
    changes = [c for c in json.loads((root / 'rank_changes.json').read_text())
               if c['condition'] == 'raw']
    improved = sum(1 for c in changes if c['real_rank'] and (not c['bm25_rank'] or c['real_rank'] < c['bm25_rank']))
    worsened = sum(1 for c in changes if c['bm25_rank'] and (not c['real_rank'] or c['real_rank'] > c['bm25_rank']))
    print(f'issues whose first-gold rank moved at all: {len(changes)}')
    print(f'  improved by the real graph: {improved}')
    print(f'  worsened by the real graph: {worsened}')
    print(f'  unchanged issues: {len({a["instance_id"] for a in audits}) - len(changes)}')

    section('graph coverage of gold files (audit.json)')
    zero_degree = [a['instance_id'] for a in audits
                   if sum(a['gold_in_degree']) + sum(a['gold_out_degree']) == 0]
    print(f'issues whose gold files have zero import degree: {len(zero_degree)}')
    print(f'total AST parse failures: {sum(len(a["index"]["parse_failures"]) for a in audits)}')
    swaps = [c for a in audits for c in a['rewiring']]
    print(f'rewiring controls: {len(swaps)}; all requested swaps completed: '
          f'{all(c["successful_swaps"] == c["requested_swaps"] for c in swaps)}')
    print(f'median retained-edge fraction: {np.median([c["retained_edge_fraction"] for c in swaps]):.4f}')
    print(f'median files per repo snapshot: {np.median([a["num_files"] for a in audits]):.0f}; '
          f'median edges: {np.median([a["num_edges"] for a in audits]):.0f}')

    section('offline construction times, median ms (offline_times.csv)')
    offline = read_csv(root / 'offline_times.csv')
    for column in ('snapshot_ms', 'ast_build_ms', 'bm25_build_ms', 'control_build_ms'):
        print(f'{column:18} {np.median([float(r[column]) for r in offline]):8.2f}')


if __name__ == '__main__':
    main()
