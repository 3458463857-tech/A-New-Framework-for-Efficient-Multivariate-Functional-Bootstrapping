import argparse
import json
import os
import re
from math import log2
from pathlib import Path

import click
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Generate a fancy color palette (e.g., a mix of vibrant and muted colors)
palette = sns.color_palette(
    "husl", 8
)  # "husl" is a colorful, perceptually uniform palette

# Set the generated palette as the default for all plots
sns.set_palette(palette)

# Set Seaborn styles (optional, to make the plots look nicer)
sns.set_style("whitegrid")  # Other options include "darkgrid", "white", etc.


def data_root_path(mode):
    if mode == "paper":
        return Path(__file__).parent / "../../../../../data/paper/"
    elif mode == "regenerated":
        return Path(__file__).parent / "../../../../../data/regenerated/"
    else:
        raise ValueError("Mode should be either `paper` or `regenerated`")


def load_data_cjp(mode):
    with open(data_root_path(mode) / "cjp21.json", "r") as f:
        data_cjp = json.load(f)

    timings_cjp = [(int(key), value) for key, value in data_cjp.items()]
    timings_cjp = pd.DataFrame(timings_cjp, columns=["bitwidth", "timing"])
    return timings_cjp


def load_data_hlut(perror, mode):
    with open(data_root_path(mode) / f"timings_hlut-{perror}.json", "r") as f:
        timings_hlut = json.load(f)

    timings_hlut = [
        (int(outer_key), int(inner_key), value)
        for outer_key, inner_dict in timings_hlut.items()
        for inner_key, value in inner_dict.items()
    ]
    timings_hlut = pd.DataFrame(timings_hlut, columns=["p", "n", "timing"])

    timings_hlut["actual_bitwidth"] = (timings_hlut["p"] - 1).apply(
        lambda x: int(log2(x))
    ) * timings_hlut["n"]
    return timings_hlut


def load_data_woppbs(mode):
    with open(data_root_path(mode) / "timings_wop-pbs.json", "r") as f:
        timings_woppbs = pd.DataFrame(json.load(f))
    # Convert index to numeric (was string)
    timings_woppbs.index = timings_woppbs.index.astype(int)
    timings_woppbs.reset_index(inplace=True, names=["bitwidth"])
    return timings_woppbs


def load_data_tbm(mode):
    with open(data_root_path(mode) / "timings_tbm.json", "r") as f:
        timings_tbm = pd.DataFrame(json.load(f))

    # Convert index to numeric (was string)
    timings_tbm.index = timings_tbm.index.astype(int)

    # Optional: sort by index
    timings_tbm = timings_tbm.sort_index()
    timings_tbm.reset_index(inplace=True, names="bitwidth")

    return timings_tbm


def plot_final_figure(timings_cjp, timings_woppbs, timings_tbm, timings_hlut, output):
    plt.figure(figsize=(10, 10))
    plt.rcParams.update(
        {
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.5,
            "grid.linestyle": "--",
            "text.usetex": False,
            "mathtext.fontset": "cm",
            "font.family": "serif",
            "font.serif": ["DejaVu Serif"],
        }
    )
    # --- plot
    ax = plt.gca()

    sns.lineplot(
        timings_cjp,
        x="bitwidth",
        y="timing",
        label="Classical PBS",
        color="blue",
        marker="o",
        linestyle="dashed",
        linewidth=2,
        ax=ax,
        markersize=7,
    )

    colors_wopbs = ["#EA8686", "#D02525", "#791515"]
    params_wopbs = ["\#8", "\#9", "\#10"]
    for i, color, index_params in zip([1, 2, 4], colors_wopbs, params_wopbs):
        sns.lineplot(
            timings_woppbs,
            x="bitwidth",
            y=f"{i} blocks",
            linestyle="dashdot",
            label=f"WoP-PBS: params {index_params}",
            marker="s",
            color=color,
            linewidth=2,
            ax=ax,
            markersize=7,
        )

    colors_gba = ["#E1BC29", "#EBD270"]
    for i in [2, 3]:
        sns.lineplot(
            timings_tbm,
            x="bitwidth",
            y=f"{i} blocks",
            linestyle="dotted",
            label=f"TBM: {i} blocks",
            marker="^",
            linewidth=2,
            ax=ax,
            markersize=7,
        )

    hlut_filtered = timings_hlut[timings_hlut["p"] == 3]
    sns.lineplot(
        hlut_filtered,
        x="actual_bitwidth",
        y="timing",
        color="#2F512A",
        label="Our Work: $s=2$",
        marker="D",
        linewidth=2,
        ax=ax,
        markersize=7,
    )
    hlut_filtered = timings_hlut[timings_hlut["p"] == 5]
    sns.lineplot(
        hlut_filtered,
        x="actual_bitwidth",
        y="timing",
        color="#5EA253",
        label="Our Work: $s=4$",
        marker="D",
        linewidth=2,
        ax=ax,
        markersize=7,
    )
    hlut_filtered = timings_hlut[timings_hlut["p"] == 17]
    sns.lineplot(
        hlut_filtered,
        x="actual_bitwidth",
        y="timing",
        color="#B3D5AE",
        label="Our Work: $s=16$",
        marker="D",
        linewidth=2,
        ax=ax,
        markersize=7,
    )

    ax.tick_params(axis="both", which="major", labelsize=15)
    ax.tick_params(axis="both", which="minor", labelsize=15)
    ax.grid(True, which="major", alpha=0.70)
    ax.grid(True, which="minor", alpha=0.50)

    from matplotlib.ticker import LogLocator, ScalarFormatter

    plt.xlabel("Bitwidth", fontsize=20, usetex=False)
    plt.ylabel("Time (ms)", fontsize=20, usetex=False)
    plt.xlim(1, 15)
    plt.ylim(5, 10000)
    plt.yscale("log")

    # legend outside
    ax.legend(
        title=r"\textbf{Method}",
        title_fontproperties={"weight": "bold", "size": 16},
        frameon=True,
        fancybox=True,
        framealpha=0.9,
        loc="lower right",
        prop={"size": 16},
    )

    plt.tight_layout()
    plt.savefig(output + "/Figure_8.png")


@click.command()
@click.option("--mode", type=click.Choice(["paper", "regenerated"]), required=True)
@click.option("--output", required=True)
def plot_figure_results_main(mode, output):
    timings_cjp = load_data_cjp(mode)
    timings_hlut = load_data_hlut(40, mode)
    timings_tbm = load_data_tbm(mode)
    timings_woppbs = load_data_woppbs(mode)
    plot_final_figure(timings_cjp, timings_woppbs, timings_tbm, timings_hlut, output)


def plot_intro_figure(timings_cjp, timings_hlut, is_log, output):
    # --- style + sizing
    plt.figure(figsize=(9, 6), dpi=180)
    plt.rcParams.update(
        {
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.5,
            "grid.linestyle": "--",
            "text.usetex": False,
            "mathtext.fontset": "cm",
            "font.family": "serif",
            "font.serif": ["DejaVu Serif"],
        }
    )

    # --- plot
    ax = plt.gca()

    # adding rough estimations for the timings of CJP at high precision
    extra = pd.DataFrame({"bitwidth": list(range(9, 12)), "timing": [1300, 3000, 8000]})
    timings_cjp = pd.concat([timings_cjp, extra])

    sns.lineplot(
        data=timings_cjp,
        x="bitwidth",
        y="timing",
        label="Classical PBS",
        color="blue",
        marker="o",
        linestyle="--",
        linewidth=2,
        markersize=7,
        ax=ax,
    )

    for p, label, color in [
        (3, "Our Work: $s=2$", "#2F512A"),
        (5, "Our Work: $s=4$", "#5EA253"),
        (17, "Our Work: $s=16$", "#B3D5AE"),
    ]:
        d = timings_hlut[timings_hlut["p"] == p]
        sns.lineplot(
            data=d,
            x="actual_bitwidth",
            y="timing",
            label=label,
            color=color,
            marker="D",
            linewidth=2.5,
            markersize=7,
            ax=ax,
        )

    # --- labels + scales
    ax.set_xlabel("Bitwidth", fontsize=20, usetex=False)
    ax.set_ylabel("Time (ms)", fontsize=20, usetex=False)
    ax.set_xlim(1, 15)
    ax.set_ylim(5, 8100)
    if is_log:
        ax.set_yscale("log")

    # nicer log ticks + minor grid
    from matplotlib.ticker import LogLocator, ScalarFormatter

    if is_log:
        ax.yaxis.set_major_locator(LogLocator(base=10.0))
        ax.yaxis.set_minor_locator(LogLocator(base=10.0, subs=(0.2, 0.4, 0.6, 0.8)))
    ax.tick_params(axis="both", which="major", labelsize=15)
    ax.tick_params(axis="both", which="minor", labelsize=15)
    ax.grid(True, which="major", alpha=0.70)
    ax.grid(True, which="minor", alpha=0.50)

    # legend outside
    ax.legend(
        title=r"\textbf{Method}",
        title_fontproperties={"weight": "bold", "size": 16},
        frameon=True,
        fancybox=True,
        framealpha=0.9,
        loc="upper left",
        prop={"size": 16},
    )

    plt.tight_layout()
    if is_log:
        plt.savefig(output + "/Figure_1b.png", bbox_inches="tight")
    else:
        plt.savefig(output + "/Figure_1a.png", bbox_inches="tight")


@click.command()
@click.option("--mode", type=click.Choice(["paper", "regenerated"]), required=True)
@click.option("--output", required=True)
def both_plot_intro_figures(mode, output):
    timings_cjp = load_data_cjp(mode)
    timings_hlut = load_data_hlut(40, mode)

    plot_intro_figure(timings_cjp, timings_hlut, True, output)
    plot_intro_figure(timings_cjp, timings_hlut, False, output)
