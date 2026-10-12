import os
import pickle

import click
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLORS = ["#ffa600", "#00a058", "#3185FC"]
TARGET_COLOR = "red"

# --- Global style settings ---
plt.rcParams.update(
    {
        "font.size": 16,  # base font size
        "axes.titlesize": 18,  # subplot titles
        "axes.labelsize": 16,  # x and y labels
        "xtick.labelsize": 14,
        "ytick.labelsize": 14,
        "legend.fontsize": 14,
        "figure.titlesize": 20,  # suptitle
        "text.usetex": False,  # enable LaTeX rendering
        "mathtext.fontset": "cm",
        "font.family": "serif",
        "font.serif": ["DejaVu Serif"],
    }
)


def draw(gamma, i_color, input, output):
    with open(
        input + f"/gamma_{gamma}.pickle",
        "rb",
    ) as f:
        data = pickle.load(f)

    DATA = pd.DataFrame.from_dict(data)

    # Grid layout
    n_cols = 3
    n_plots = len(DATA.columns)
    n_rows = (n_plots + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 10))
    axes = axes.flatten()

    for i, col in enumerate(DATA.columns):
        value_counts = DATA[col].value_counts().sort_index()
        target = 2 ** int(col)

        # Build full counts from 1..target
        full_index = np.arange(1, target + 1)
        counts_full = pd.Series(0, index=full_index, dtype=int)
        counts_full.update(value_counts)

        # Indices with non-zero counts
        nonzero_idx = counts_full[counts_full > 0].index.to_numpy()

        # Preferred window: last 15 values up to target
        preferred_start = max(1, target - 14)

        # Determine dynamic start to guarantee visibility of at least two non-empty bars:
        # - If >=2 non-empty bars exist, start at the *second-last* non-empty index.
        # - If exactly 1 exists, start at that index-1 (clamped to 1).
        # - If none exist, fall back to last two positions.
        if len(nonzero_idx) >= 2:
            dyn_start = int(nonzero_idx[-2])
        elif len(nonzero_idx) == 1:
            dyn_start = max(1, int(nonzero_idx[0]) - 1)
        else:
            dyn_start = max(1, target - 1)

        # Final start: use the earlier (more left) of preferred_start and dyn_start
        # so that we keep a tight window when possible, but expand left as needed
        # to include the second non-empty bar.
        start = min(preferred_start, dyn_start)

        # Compose windowed counts
        window_index = np.arange(start, target + 1)
        counts = counts_full.loc[window_index]

        # Colors (highlight target if present)
        colors = [COLORS[i_color]] * len(counts)
        if counts.get(target, 0) > 0:
            colors[-1] = TARGET_COLOR
        else:
            axes[i].annotate(
                r"\textit{No solution}",
                xy=(target, 0),
                xytext=(target, (counts.max() if counts.max() > 0 else 1) * 0.2),
                ha="center",
                fontsize=12,
                arrowprops=dict(facecolor="black", shrink=0.05),
            )

        axes[i].bar(counts.index, counts.values, color=colors)
        axes[i].set_title(rf"$n={col},\ \ target=2^{{{int(col)}}}$")
        axes[i].set_xlabel(r"Rank")
        axes[i].set_ylabel(r"Count")
        axes[i].set_xlim(start - 0.5, target + 0.5)

    # Turn off extra axes
    for j in range(n_plots, len(axes)):
        axes[j].axis("off")

    plt.tight_layout()
    plt.savefig(output + f"/Figure_5_gamma={gamma}.png")


@click.command()
@click.option("--input", required=True)
@click.option("--output", required=True)
def plot(input, output):
    draw(1, 0, input, output)
    draw(1.05, 1, input, output)
    draw(1.1, 2, input, output)
