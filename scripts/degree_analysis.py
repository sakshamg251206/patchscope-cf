"""Does one-hop import propagation help, or is it a popularity prior in disguise?

Splits issues by the import in-degree of their gold file and reports, per quartile, the
paired Hit@5 difference of the real graph against BM25 and against the degree-preserving
rewired control, with bootstrap intervals.

The prediction the counterfactual design makes: if propagation works by moving score onto
heavily imported hub modules, then it should help exactly when the file being searched for
*is* such a hub, hurt otherwise, and a degree-matched random graph should show the same
pattern because it transfers score onto the same popular nodes.

Usage: python scripts/degree_analysis.py [results/full300]
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

from patchscope.evaluate import paired_bootstrap, write_csv

QUANTILES = (0.25, 0.50, 0.75)
LABELS = ("Q1 (least imported)", "Q2", "Q3", "Q4 (most imported)")


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "results/full300")
    audits = {a["instance_id"]: a for a in json.loads((root / "audit.json").read_text())}
    rows = [r for r in csv.DictReader((root / "per_instance.csv").open()) if r["condition"] == "raw"]

    scores: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        scores.setdefault((row["instance_id"], row["method"]), []).append(float(row["hit5"]))

    # In-degree of the gold file(s): how many other indexed files import it.
    degree = {issue: sum(audit["gold_in_degree"]) for issue, audit in audits.items()}
    cuts = np.quantile(np.array(sorted(degree.values())), QUANTILES)

    def bucket(value: float) -> int:
        return int(np.searchsorted(cuts, value, side="left"))

    groups: dict[int, list[str]] = {}
    for issue, value in degree.items():
        groups.setdefault(bucket(value), []).append(issue)

    table = []
    for index in sorted(groups):
        issues = sorted(groups[index])
        mean = {m: float(np.mean([np.mean(scores[(i, m)]) for i in issues]))
                for m in ("bm25", "real", "rewired", "edge_drop")}
        paired = {m: [float(np.mean(scores[(i, "real")])) - float(np.mean(scores[(i, m)]))
                      for i in issues] for m in ("bm25", "rewired")}
        entry = dict(group=LABELS[index], n=len(issues),
                     in_degree_min=int(min(degree[i] for i in issues)),
                     in_degree_max=int(max(degree[i] for i in issues)),
                     **{f"{m}_hit5": 100 * v for m, v in mean.items()})
        for control, values in paired.items():
            stats = paired_bootstrap(np.array(values), np.zeros(len(values)))
            entry[f"real_minus_{control}_pp"] = stats["difference_pp"]
            entry[f"real_minus_{control}_lo"] = stats["lower_pp"]
            entry[f"real_minus_{control}_hi"] = stats["upper_pp"]
        table.append(entry)

    write_csv(root / "by_gold_in_degree.csv", table)
    header = f'{"group":22}{"n":>5}{"in-deg":>9}{"bm25":>7}{"real":>7}{"rewired":>9}'
    print(header + f'{"real-bm25 [95% CI]":>26}{"real-rewired [95% CI]":>26}')
    for entry in table:
        span = f'{entry["in_degree_min"]}-{entry["in_degree_max"]}'
        a = '{:+.1f} [{:+.1f},{:+.1f}]'.format(entry["real_minus_bm25_pp"],
                                               entry["real_minus_bm25_lo"], entry["real_minus_bm25_hi"])
        b = '{:+.1f} [{:+.1f},{:+.1f}]'.format(entry["real_minus_rewired_pp"],
                                               entry["real_minus_rewired_lo"], entry["real_minus_rewired_hi"])
        print(f'{entry["group"]:22}{entry["n"]:>5}{span:>9}{entry["bm25_hit5"]:>7.1f}'
              f'{entry["real_hit5"]:>7.1f}{entry["rewired_hit5"]:>9.1f}{a:>26}{b:>26}')

    plot(table, root)
    print(f'\nwrote {root}/by_gold_in_degree.csv and {root}/figures/gold_in_degree.png')


def plot(table: list[dict], root: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    (root / "figures").mkdir(parents=True, exist_ok=True)
    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 4))
    positions = np.arange(len(table))
    width = 0.26
    for offset, (method, color) in enumerate((("bm25", "#555555"), ("real", "#006e90"),
                                              ("rewired", "#d17a22"))):
        left.bar(positions + (offset - 1) * width, [e[f"{method}_hit5"] for e in table],
                 width, label=method, color=color)
    left.set_xticks(positions, [f'{e["group"]}\n(n={e["n"]})' for e in table], fontsize=8)
    left.set_ylabel("Hit@5 (%)")
    left.set_title("Hit@5 by import in-degree of the gold file", fontsize=11)
    left.legend(frameon=False, ncols=3)
    left.grid(axis="y", alpha=0.2)
    left.set_axisbelow(True)

    for control, color in (("bm25", "#555555"), ("rewired", "#d17a22")):
        mid = np.array([e[f"real_minus_{control}_pp"] for e in table])
        low = np.array([e[f"real_minus_{control}_lo"] for e in table])
        high = np.array([e[f"real_minus_{control}_hi"] for e in table])
        shift = -0.07 if control == "bm25" else 0.07
        right.errorbar(positions + shift, mid, yerr=[mid - low, high - mid], marker="o",
                       capsize=4, linestyle="-", color=color, label=f"real − {control}")
    right.axhline(0, color="gray", linestyle="--", linewidth=1)
    right.set_xticks(positions, [e["group"].split(" ")[0] for e in table])
    right.set_ylabel("Paired Hit@5 difference (pp)")
    right.set_title("Propagation helps only for already-popular files", fontsize=11)
    right.legend(frameon=False)
    right.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(root / "figures" / "gold_in_degree.png", dpi=180)
    plt.close(figure)


if __name__ == "__main__":
    main()
