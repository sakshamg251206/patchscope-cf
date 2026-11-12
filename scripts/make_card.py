"""Build the 560x280 card/thumbnail image the Kaggle Writeup form asks for.

Numbers are read from the saved result artifacts, not typed in, so the card cannot
disagree with the paper.

Usage: python scripts/make_card.py [results/full300]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

INK = "#14181f"
MUTED = "#5b6472"
BM25 = "#555555"
REAL = "#006e90"
REWIRED = "#d17a22"


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "results/full300")
    summary = {(r["condition"], r["method"]): r
               for r in csv.DictReader((root / "summary.csv").open())}
    degree = list(csv.DictReader((root / "by_gold_in_degree.csv").open()))
    n = summary[("raw", "bm25")]["n"]
    hit5 = {m: 100 * float(summary[("raw", m)]["hit5"]) for m in ("bm25", "real", "rewired")}

    figure = plt.figure(figsize=(5.6, 2.8), dpi=100)
    figure.patch.set_facecolor("white")

    figure.text(0.05, 0.95, "Do code graphs really help locate bugs?",
                fontsize=13, fontweight="bold", color=INK, va="top")
    figure.text(0.05, 0.80, f"PatchScope-CF  ·  all {n} SWE-bench Lite test issues  ·  CPU-only, no model",
                fontsize=7, color=MUTED, va="top")

    # Left: the headline comparison, including the control that makes the point.
    figure.text(0.05, 0.655, "Hit@5 (%)", fontsize=7, color=MUTED, va="top")
    axis = figure.add_axes([0.05, 0.30, 0.36, 0.33])
    labels = ["BM25", "import\ngraph", "random,\nsame degrees"]
    values = [hit5["bm25"], hit5["real"], hit5["rewired"]]
    bars = axis.bar(range(3), values, color=[BM25, REAL, REWIRED], width=0.6)
    for bar, value in zip(bars, values):
        axis.text(bar.get_x() + bar.get_width() / 2, value + 1.5, f"{value:.1f}",
                  ha="center", fontsize=7.5, color=INK, fontweight="bold")
    axis.set_xticks(range(3), labels, fontsize=6, color=MUTED)
    axis.set_ylim(0, 74)
    axis.set_yticks([])
    for side in ("top", "right", "left"):
        axis.spines[side].set_visible(False)
    axis.spines["bottom"].set_color("#d6dae1")
    axis.tick_params(length=0, pad=1)

    # Right: the mechanism — propagation only pays off for already-popular files.
    figure.text(0.56, 0.655, "graph − BM25 (pp), by how often the\ntarget file is imported",
                fontsize=7, color=MUTED, va="top", linespacing=1.4)
    axis2 = figure.add_axes([0.56, 0.30, 0.39, 0.28])
    diffs = [float(r["real_minus_bm25_pp"]) for r in degree]
    axis2.bar(range(len(diffs)), diffs,
              color=["#b3261e" if d < 0 else "#1e7a46" for d in diffs], width=0.6)
    axis2.axhline(0, color="#9aa3b0", linewidth=0.8)
    axis2.set_xticks(range(len(diffs)),
                     ["least\nimported", "", "", "most\nimported"], fontsize=6, color=MUTED)
    axis2.set_yticks([])
    axis2.set_ylim(min(diffs) - 9, max(diffs) + 9)
    for side in ("top", "right", "left", "bottom"):
        axis2.spines[side].set_visible(False)
    axis2.tick_params(length=0, pad=1)
    axis2.text(0, diffs[0] - 1.5, f"{diffs[0]:.0f}", ha="center", va="top",
               fontsize=7.5, color="#b3261e", fontweight="bold")
    axis2.text(3, diffs[3] + 1.5, f"+{diffs[3]:.0f}", ha="center", va="bottom",
               fontsize=7.5, color="#1e7a46", fontweight="bold")

    figure.text(0.05, 0.035,
                "A degree-preserving rewired graph matches the real one:\n"
                "one-hop import propagation is a popularity prior.",
                fontsize=7, color=INK, va="bottom", linespacing=1.45)

    out = root / "figures" / "kaggle_card.png"
    figure.savefig(out, dpi=100, facecolor="white")
    plt.close(figure)
    from PIL import Image  # optional check; skipped if Pillow is absent
    print(f"wrote {out} at {Image.open(out).size}")


if __name__ == "__main__":
    try:
        main()
    except ImportError:
        print("wrote card (install Pillow to verify exact pixel size)")
