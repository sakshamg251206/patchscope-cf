"""Check that the paper's headline table and word count agree with the saved results.

Guards against the most dangerous failure mode in a write-up: prose drifting away from
the artifacts it cites. Compares every row of the Markdown results table in the paper
against `summary.csv`, and enforces the competition's 3,000-word limit.

Usage: python scripts/check_paper.py [paper/KAGGLE_WRITEUP.md] [results/full300]
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

TOLERANCE = 0.051  # the paper rounds to one decimal place


def table_rows(markdown: str) -> list[dict[str, str]]:
    """Every pipe-table row whose first two cells are a known condition and method."""
    rows = []
    for line in markdown.splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 7 and cells[0] in {'raw', 'masked'} and cells[1] in {
                'bm25', 'real', 'rewired', 'edge_drop'}:
            rows.append(dict(condition=cells[0], method=cells[1], n=cells[2],
                             hit1=cells[3], hit5=cells[4], hit10=cells[5],
                             mrr10=cells[6], recall5=cells[7] if len(cells) > 7 else None))
    return rows


def main() -> int:
    paper = Path(sys.argv[1] if len(sys.argv) > 1 else 'paper/KAGGLE_WRITEUP.md')
    results = Path(sys.argv[2] if len(sys.argv) > 2 else 'results/full300')
    text = paper.read_text()
    summary = {(r['condition'], r['method']): r
               for r in csv.DictReader((results / 'summary.csv').open())}

    rows = table_rows(text)
    if len(rows) != len(summary):
        print(f'FAIL: paper has {len(rows)} result rows, summary.csv has {len(summary)}')
        return 1
    for row in rows:
        saved = summary[(row['condition'], row['method'])]
        if int(row['n']) != int(saved['n']):
            print(f'FAIL: n mismatch for {row["condition"]}/{row["method"]}')
            return 1
        for metric in ('hit1', 'hit5', 'hit10', 'recall5'):
            if row[metric] is None:
                continue
            claimed = float(row[metric].rstrip('%'))
            if abs(claimed - 100 * float(saved[metric])) > TOLERANCE:
                print(f'FAIL: {metric} for {row["condition"]}/{row["method"]}: '
                      f'paper {claimed} vs results {100*float(saved[metric]):.4f}')
                return 1
        if abs(float(row['mrr10']) - float(saved['mrr10'])) > 0.00051:
            print(f'FAIL: mrr10 for {row["condition"]}/{row["method"]}')
            return 1

    # Word count excludes the Markdown table and image/reference clutter only loosely;
    # counting everything is the conservative direction for a maximum.
    words = len(re.sub(r'\s+', ' ', text).split())
    print(f'paper table matches {results}/summary.csv ({len(rows)} rows)')
    print(f'word count (whitespace, whole file): {words}')
    if words > 3000:
        print('FAIL: over the 3,000-word competition limit')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
