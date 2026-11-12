"""Development-split-only sensitivity sweep over the graph weight and seed budget.

Why this exists: the frozen protocol fixes alpha=0.5 and a 20-file seed budget. If the
real import graph underperforms BM25 at those settings, the result could mean either
(a) the propagation weight is badly chosen, or (b) the topology carries no usable
ranking signal. This sweep separates the two WITHOUT touching test labels: it runs
only on the SWE-bench Lite *dev* split, which shares no repository with the frozen
test cohort. Nothing here feeds back into the frozen test configuration.

Usage: python scripts/dev_sensitivity.py [--output results/dev_sensitivity.csv]
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from patchscope.data import fetch_dataset, snapshot
from patchscope.evaluate import metrics
from patchscope.graph import rewire
from patchscope.index import build_index, tokenize
from patchscope.labels import gold_paths
from patchscope.retrieve import BM25, rank

ALPHAS = (0.0, 0.1, 0.25, 0.5, 0.75, 1.0)
SEED_BUDGETS = (5, 10, 20, 50)
REWIRE_SEED = 2026


def sweep(cache: Path) -> list[dict]:
    rows, _ = fetch_dataset(cache, "dev")
    records: list[dict] = []
    for case in sorted(rows, key=lambda r: r["instance_id"]):
        files, _ = snapshot(case["repo"], case["base_commit"], cache)
        labels = gold_paths(case["patch"])
        gold = [path for path in labels if path in files]
        if not labels or len(gold) != len(labels):
            continue  # same eligibility rule as the main evaluator; no replacement
        index = build_index(files)
        model = BM25(index.tokens)
        scores = model.scores(tokenize(case["problem_statement"]))
        control, _ = rewire(index.graph, REWIRE_SEED)
        # "reverse" propagates to importers instead of imported modules: it tests whether
        # the fixed protocol simply chose the wrong edge direction.
        reverse = index.graph.reverse(copy=True)
        for alpha in ALPHAS:
            for seeds in SEED_BUDGETS:
                for name, graph in (("real", index.graph), ("rewired", control),
                                    ("real_reverse", reverse)):
                    predicted = rank(index.paths, scores, graph, 100, seeds, alpha)
                    records.append(dict(instance_id=case["instance_id"], repo=case["repo"],
                                        method=name, alpha=alpha, seed_budget=seeds,
                                        **metrics(predicted, gold)))
        print(f"swept {case['instance_id']}", flush=True)
    return records


def aggregate(records: list[dict]) -> list[dict]:
    table = []
    for alpha in ALPHAS:
        for seeds in SEED_BUDGETS:
            for method in ("real", "rewired", "real_reverse"):
                subset = [r for r in records
                          if r["alpha"] == alpha and r["seed_budget"] == seeds and r["method"] == method]
                if not subset:
                    continue
                table.append(dict(method=method, alpha=alpha, seed_budget=seeds, n=len(subset),
                                  **{m: float(np.mean([r[m] for r in subset]))
                                     for m in ("hit1", "hit5", "hit10", "mrr10")}))
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path("data/cache"))
    parser.add_argument("--output", type=Path, default=Path("results/dev_sensitivity"))
    args = parser.parse_args()
    records = sweep(args.cache)
    if not records:
        raise SystemExit("no eligible dev cases")
    table = aggregate(records)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "per_instance.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    with (args.output / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    (args.output / "config.json").write_text(json.dumps(
        dict(split="dev", alphas=list(ALPHAS), seed_budgets=list(SEED_BUDGETS),
             rewire_seed=REWIRE_SEED, candidate_budget=100,
             note="dev-only sensitivity; test configuration remains frozen at alpha=0.5, seeds=20"),
        indent=2, sort_keys=True) + "\n")
    plot(table, args.output)
    best = max(table, key=lambda r: r["hit5"])
    print(json.dumps(dict(cases=len({r['instance_id'] for r in records}),
                          best_cell_in_grid=best), indent=2))


def plot(table: list[dict], output: Path) -> None:
    """Metric versus graph weight at the frozen seed budget, with the seed-budget range."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"real": "#006e90", "real_reverse": "#2a9d4a", "rewired": "#d17a22"}
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    figure, axes = plt.subplots(1, 2, figsize=(11, 4))
    for axis, metric, label in ((axes[0], "hit5", "Hit@5 (%)"), (axes[1], "mrr10", "MRR@10")):
        scale = 100 if metric == "hit5" else 1
        for method, color in colors.items():
            frozen, low, high = [], [], []
            for alpha in ALPHAS:
                cells = [r[metric] * scale for r in table if r["method"] == method and r["alpha"] == alpha]
                frozen.append(next(r[metric] * scale for r in table
                                   if r["method"] == method and r["alpha"] == alpha and r["seed_budget"] == 20))
                low.append(min(cells))
                high.append(max(cells))
            style = {"real": "-", "real_reverse": ":", "rewired": "--"}[method]
            axis.plot(ALPHAS, frozen, marker="o", linestyle=style, color=color, label=method,
                      linewidth=2.2 if method == "real" else 1.6,
                      zorder=3 if method == "real" else 2)
            axis.fill_between(ALPHAS, low, high, color=color, alpha=0.12)
        axis.set_xlabel("Graph weight alpha  (0 = pure lexical ranking)")
        axis.set_ylabel(label)
        axis.grid(alpha=0.2)
    axes[1].legend(frameon=False)
    figure.suptitle("Dev split only (n=23): line = frozen 20-file seed budget, band = range over 5/10/20/50", fontsize=10)
    figure.tight_layout()
    figure.savefig(output / "dev_sensitivity.png", dpi=180)
    plt.close(figure)


if __name__ == "__main__":
    main()
