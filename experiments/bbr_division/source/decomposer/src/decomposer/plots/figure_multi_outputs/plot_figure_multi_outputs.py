import json
import math
import os

import click
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# --- load & prep once ---
def load_data(input):
    with open(
        os.path.join(input, "timings_hlut_partial_evaluations-40.json"), "r"
    ) as f:
        data = json.load(f)

    rows = []
    for p_key in data:
        for n_key in data[p_key]:
            for m_key in data[p_key][n_key]:
                rows.append([p_key, n_key, m_key, data[p_key][n_key][m_key]])

    df = pd.DataFrame(rows, columns=["p", "n", "m", "timing"]).astype(int)
    return df


def plot_timings_line(
    df: pd.DataFrame,
    p: int,
    n_min: int,
    n_max: int,
    color: str = "C0",
    outfile: str = "fig_multi_outputs.png",
    fixed_rows: int | None = None,
    fixed_cols: int | None = None,
    marker: str = "D",  # diamond markers
    markersize: float = 6,
    linewidth: float = 1.8,
):
    """
    Line plots of timing vs m for each n in [n_min, n_max] at fixed p.
    - color: matplotlib color string (e.g., 'C0', 'black', '#1f77b4', etc.)
    - marker: matplotlib marker (default 'D' for diamond)
    """
    ns = list(range(int(n_min), int(n_max) + 1))
    n_plots = len(ns)

    if fixed_rows is None or fixed_cols is None:
        n_cols = int(math.ceil(math.sqrt(n_plots)))
        n_rows = int(math.ceil(n_plots / n_cols))
    else:
        n_rows, n_cols = fixed_rows, fixed_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4.8 * n_cols, 3.8 * n_rows))
    axes = np.atleast_1d(axes).ravel()

    for idx, n in enumerate(ns):
        ax = axes[idx]
        dff = df[(df["p"] == p) & (df["n"] == n)].sort_values("m")
        ax.plot(
            dff["m"],
            dff["timing"],
            marker=marker,
            markersize=markersize,
            linewidth=linewidth,
            color=color,
        )
        ax.set_ylim(bottom=0)
        ax.set_title(f"n = {n}")
        ax.set_xlabel("Bitwidth output")
        ax.set_ylabel("Time (ms)")
        ax.grid(True, linestyle="--", alpha=0.4)

    # Hide any extra axes (e.g., bottom-right if grid is larger than needed)
    for j in range(n_plots, len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()
    plt.savefig(outfile, dpi=150)
    plt.close(fig)


@click.command()
@click.option("--input", required=True)
@click.option("--output", required=True)
def plot(input, output):
    df = load_data(input)
    # --- example usage ---
    plot_timings_line(
        df,
        p=3,
        n_min=4,
        n_max=14,
        color="green",
        outfile=os.path.join(output, "Figure_9_p_3.png"),
    )
    plot_timings_line(
        df,
        p=5,
        n_min=3,
        n_max=7,
        color="lightgreen",
        outfile=os.path.join(output, "Figure_9_p_5.png"),
    )
    plot_timings_line(
        df,
        p=17,
        n_min=2,
        n_max=3,
        color="gold",
        outfile=os.path.join(output, "Figure_9_p_17.png"),
    )
