import pathlib
import pickle

import click
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import seaborn as sns

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


def load_data(input):
    with open(f"{input}/results.pickle", "rb") as f:
        results = pickle.load(f)

    df = pd.DataFrame(results, columns=["s", "p", "n", "l", "t", "rank"])

    df["n_cols"] = (df["n"] + df["l"]) * (df["t"] + 1)
    df["n_rows"] = df["s"] ** df["n"]

    df["margin"] = df["n_cols"] - df["n_rows"]
    df["relative_margin"] = df["n_cols"] / df["n_rows"]
    df["rank_defect"] = df["n_rows"] - df["rank"]
    df["relative_rank_defect"] = df["rank_defect"] / df["n_rows"]
    df["full-rankness"] = np.where(df["rank_defect"] == 0, "full rank", "rank defect")
    # Binary target: 1 if full rank, 0 otherwise
    df = df[np.isfinite(df["relative_margin"])].copy()
    return df


def plot_rank_defect(dataframe, x_col, filename, x_range=None):
    data = dataframe
    if x_range is not None:
        xmin, xmax = x_range
        data = data[(data[x_col] >= xmin) & (data[x_col] <= xmax)]

    is_zero = data["relative_rank_defect"] == 0
    non_zero = ~is_zero

    plt.figure()

    # Non-zero points in orange (complementary to blue)
    sns.scatterplot(
        data=data[non_zero],
        x=x_col,
        y="relative_rank_defect",
        s=2,
        linewidth=0,
        marker=",",
        edgecolor=None,
        alpha=0.6,
        color="#ff7f0e",
        rasterized=True,
    )

    # Zero points in blue
    sns.scatterplot(
        data=data[is_zero],
        x=x_col,
        y="relative_rank_defect",
        s=2,
        linewidth=0,
        marker=",",
        edgecolor=None,
        alpha=0.9,
        color="#1f77b4",
        rasterized=True,
        zorder=3,
    )

    if x_range is not None:
        plt.xlim(x_range)

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close()


def histplot(dataframe, filename):
    sns.set_theme(style="ticks")

    f, ax = plt.subplots(figsize=(7, 5))
    sns.despine(f)

    sns.histplot(
        dataframe,
        x="relative_margin",
        hue="full-rankness",
        # bins=50,
        binrange=(1, 2),  # e.g., (1.0, 1.2) if using relative_margin
        multiple="fill",  # per-bin fractions (stacked to 1)
        element="bars",
        stat="count",
        palette={"full rank": "#1f77b4", "rank defect": "#ff7f0e"},
        alpha=0.9,
        shrink=0.9,
        ax=ax,
    )
    ax.xaxis.set_major_formatter(mpl.ticker.ScalarFormatter())
    plt.xticks([1.0, 1.2, 1.4, 1.6, 1.8, 2.0])
    ax.set_xlabel(r"Relative Margin: $\frac{(t+1)(n+\lambda) - s^n}{s^n}$")
    ax.set_ylabel(r"Frequency")
    plt.savefig(filename, dpi=300)


# --- 2) Binned correlation between relative_margin and P(full rank) ---
def binned_fullrank_corr(df, *, bins=50, x_range=None, method="quantile"):
    """
    Returns (r_weighted, table) where:
      - r_weighted is the weighted Pearson correlation between bin-center (or mean x in bin)
        and per-bin probability of full rank, weighted by bin counts.
      - table has columns ['x_bin', 'p_full', 'n'].
    method: 'quantile' (equal-count bins) or 'uniform' (equal-width bins).
    """
    d = df[np.isfinite(df["relative_margin"])].copy()
    d["full"] = (d["rank_defect"] == 0).astype(int)

    if method == "quantile":
        # Equal-count bins -> stable estimates for p
        q = min(bins, d.shape[0])  # guard if few rows
        bins_actual = max(2, int(q))
        cats, edges = pd.qcut(
            d["relative_margin"], q=bins_actual, retbins=True, duplicates="drop"
        )
        d["_bin"] = cats
        gb = d.groupby("_bin", observed=True)
        x_bin = gb["relative_margin"].mean().to_numpy()
    else:
        # Equal-width bins over range
        if x_range is None:
            xmin, xmax = (
                float(d["relative_margin"].min()),
                float(d["relative_margin"].max()),
            )
        else:
            xmin, xmax = x_range
        edges = np.linspace(xmin, xmax, bins + 1)
        # Assign bins
        idx = np.digitize(d["relative_margin"], edges, right=False) - 1
        m = (idx >= 0) & (idx < bins)
        d = d.loc[m].copy()
        d["_bin"] = idx[m]
        gb = d.groupby("_bin", observed=True)
        centers = 0.5 * (edges[:-1] + edges[1:])
        x_bin = centers[gb.size().index]

    p_full = gb["full"].mean().to_numpy()
    n = gb.size().to_numpy()

    # Weighted Pearson correlation between x_bin and p_full
    w = n.astype(float)
    if w.sum() == 0:
        r_w = np.nan
    else:
        w /= w.sum()
        mx = np.sum(w * x_bin)
        my = np.sum(w * p_full)
        cov = np.sum(w * (x_bin - mx) * (p_full - my))
        vx = np.sum(w * (x_bin - mx) ** 2)
        vy = np.sum(w * (p_full - my) ** 2)
        r_w = cov / np.sqrt(vx * vy) if vx > 0 and vy > 0 else np.nan

    table = pd.DataFrame({"x_bin": x_bin, "p_full": p_full, "n": n})
    return r_w, table, edges


@click.command()
@click.option("--input", required=True)
@click.option("--output", required=True)
def plot_figure_correlation(input, output):
    df = load_data(input)
    histplot(
        df,
        filename=f"{output}/Figure_6.png",
    )
