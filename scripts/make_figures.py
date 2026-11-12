"""Two publication figures the standard report does not produce.

1. `by_repo_hit5.png` — Hit@5 per repository, so a reader can see whether the pooled
   effect is driven by one repository or is consistent across them.
2. `budget_effect.png` — the paired real-minus-BM25 and real-minus-rewired Hit@k
   difference with 95% bootstrap intervals as a function of the returned-file budget.
   This is the figure behind the claim that the sign of the graph effect depends on k.

Run `scripts/budget_analysis.py` first; this script reads its CSV.

Usage: python scripts/make_figures.py [results/full300]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

COLORS = {"bm25": "#555555", "real": "#006e90", "rewired": "#d17a22", "edge_drop": "#825ca6"}


def by_repo(root: Path, condition: str = "raw") -> None:
    rows = [r for r in csv.DictReader((root / "by_repo.csv").open()) if r["condition"] == condition]
    repos = sorted({r["repo"] for r in rows},
                   key=lambda name: -int(next(r["n"] for r in rows if r["repo"] == name)))
    methods = ("bm25", "real", "rewired")
    width = 0.26
    figure, axis = plt.subplots(figsize=(10, 4))
    positions = np.arange(len(repos))
    for offset, method in enumerate(methods):
        values = [100 * float(next(r["hit5"] for r in rows if r["repo"] == repo and r["method"] == method))
                  for repo in repos]
        axis.bar(positions + (offset - 1) * width, values, width, label=method, color=COLORS[method])
    labels = [f'{repo.split("/")[-1]}\n(n={next(r["n"] for r in rows if r["repo"] == repo)})' for repo in repos]
    axis.set_xticks(positions, labels, fontsize=9)
    axis.set_ylabel("Hit@5 (%)")
    axis.set_title(f"Hit@5 by repository, {condition} queries", fontsize=11)
    axis.legend(frameon=False, ncols=3)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    figure.tight_layout()
    figure.savefig(root / "figures" / "by_repo_hit5.png", dpi=180)
    plt.close(figure)


def budget_effect(root: Path, condition: str = "raw") -> None:
    rows = [r for r in csv.DictReader((root / "budget_comparisons.csv").open())
            if r["condition"] == condition]
    figure, axis = plt.subplots(figsize=(8, 4))
    for control, color, dx in (("bm25", COLORS["bm25"], -0.04), ("rewired", COLORS["rewired"], 0.04)):
        subset = sorted((r for r in rows if r["control"] == control), key=lambda r: int(r["k"]))
        ks = np.array([int(r["k"]) for r in subset], dtype=float)
        mid = np.array([float(r["difference_pp"]) for r in subset])
        low = np.array([float(r["lower_pp"]) for r in subset])
        high = np.array([float(r["upper_pp"]) for r in subset])
        axis.errorbar(ks * (1 + dx), mid, yerr=[mid - low, high - mid], marker="o",
                      capsize=3, color=color, label=f"real − {control}")
    axis.axhline(0, color="gray", linestyle="--", linewidth=1)
    axis.set_xscale("log")
    axis.set_xticks([1, 3, 5, 10, 20, 50, 100], ["1", "3", "5", "10", "20", "50", "100"])
    axis.set_xlabel("Returned file budget k (candidate pool fixed at 100)")
    axis.set_ylabel("Paired Hit@k difference (pp)")
    axis.set_title(f"Graph effect versus output budget, {condition} queries (95% paired bootstrap)",
                   fontsize=11)
    axis.legend(frameon=False)
    axis.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(root / "figures" / "budget_effect.png", dpi=180)
    plt.close(figure)


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "results/full300")
    (root / "figures").mkdir(parents=True, exist_ok=True)
    by_repo(root)
    budget_effect(root)
    print(f'wrote {root}/figures/by_repo_hit5.png and {root}/figures/budget_effect.png')


if __name__ == "__main__":
    main()
