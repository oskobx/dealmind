"""Render docs/results.png from a run folder: the learning curve per supplier and the Ridgeline test.

    uv run scripts/make_chart.py [runs/demo2] [docs/results.png]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Same colors as the web page.
COLORS = {
    "northwood": "#2a78d6",
    "quickfurn": "#d4521f",
    "harlow": "#0d8f5e",
    "valuecraft": "#a86f00",
}
INK, MUTED, GRID = "#1f2328", "#5b6470", "#e3e6ea"
BAR_BLANK, BAR_INFORMED = "#b8bec6", "#2a78d6"


def main() -> None:
    run_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/demo2")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "docs/results.png")
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    ridgeline = json.loads((run_dir / "ridgeline.json").read_text(encoding="utf-8"))

    plt.rcParams.update({"font.size": 12, "axes.titlesize": 14, "axes.labelsize": 12, "font.family": "sans-serif"})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [2.2, 1]}, facecolor="white")

    # Panel 1: learning curve, best-so-far per supplier, tested score as a faint dashed line
    rounds = None
    ends: list[tuple[float, str]] = []  # (final best-so-far, label) for collision-free end labels
    for key, s in state["suppliers"].items():
        tested = s["scores"]
        rounds = list(range(1, len(tested) + 1))
        best_so_far, best = [], 0.0
        for x in tested:
            best = max(best, x)
            best_so_far.append(best)
        color = COLORS.get(key, INK)
        ax1.plot(rounds, tested, linestyle="--", linewidth=1.2, color=color, alpha=0.35, zorder=2)
        ax1.plot(rounds, best_so_far, linewidth=2.2, color=color, marker="o", markersize=6, markeredgecolor="white", markeredgewidth=1.5, label=s["name"], zorder=3)
        ends.append((best_so_far[-1], f"{s['name']}  {best_so_far[-1]:.1f}"))
    # Direct labels at the line ends, pushed apart so none overlap (minimum gap in score units).
    min_gap = 4.0
    placed: list[float] = []
    for value, _ in sorted(ends):
        y = value if not placed else max(value, placed[-1] + min_gap)
        placed.append(y)
    for (value, label), y in zip(sorted(ends), placed):
        ax1.annotate(label, (rounds[-1], value), xytext=(8, (y - value) * 3.1), textcoords="offset points", va="center", fontsize=11, color=INK)
    ax1.set_title("Learning curve: best card so far per supplier", loc="left", color=INK, pad=12)
    ax1.set_xlabel("Training round")
    ax1.set_ylabel("Deal score (70 = every target hit)")
    ax1.set_xticks(rounds or [])
    right = (rounds[-1] if rounds else 5) + 2.2
    ax1.set_xlim(0.8, right)
    ax1.set_ylim(0, 100)
    ax1.axhline(70, color=GRID, linewidth=1, zorder=1)
    ax1.text(right - 0.1, 67.5, "target 70", fontsize=10, color=MUTED, ha="right", va="top")
    ax1.grid(axis="y", color=GRID, linewidth=0.8)
    ax1.plot([], [], linestyle="--", color=MUTED, alpha=0.6, label="tested each round")
    ax1.legend(loc="lower right", frameon=False, fontsize=10)

    # Panel 2: Ridgeline, blank vs informed
    arms = ridgeline["arms"]
    labels = ["blank\nspecialist", "informed by\nthe playbook"]
    values = [arms["blank"]["mean"], arms["informed"]["mean"]]
    bars = ax2.bar(labels, values, color=[BAR_BLANK, BAR_INFORMED], width=0.55, zorder=3)
    for bar, value in zip(bars, values):
        ax2.text(bar.get_x() + bar.get_width() / 2, value + 1.5, f"{value:.1f}", ha="center", va="bottom", fontsize=13, color=INK, fontweight="bold")
    ax2.set_title("Ridgeline: supplier never seen before", loc="left", color=INK, pad=12)
    ax2.set_ylabel("Mean deal score, same 3 deals")
    ax2.set_ylim(0, 100)
    ax2.axhline(70, color=GRID, linewidth=1, zorder=1)
    ax2.grid(axis="y", color=GRID, linewidth=0.8)
    difference = values[1] - values[0]
    ax2.text(0.5, 0.95, f"{difference:+.1f} points from the general tactics alone", transform=ax2.transAxes, ha="center", va="top", fontsize=11, color=MUTED)

    for ax in (ax1, ax2):
        ax.set_facecolor("white")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(GRID)
        ax.tick_params(colors=MUTED, labelcolor=INK)
        ax.set_axisbelow(True)

    fig.tight_layout(w_pad=3)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, facecolor="white")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
