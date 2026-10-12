import json
import os
import pickle
from math import ceil, floor, sqrt

import click
import galois
import numpy as np

from decomposer.chain import Chain, ChainParallel
from decomposer.encoding import Encoding
from decomposer.gauss import check_rank_drop, solve_overdetermined_linear_system
from decomposer.shape_decomposition import next_t_i, optimal_shape
from decomposer.utils.utils import face_splitting


####################### Useful API ##################################
def generate_one_random_matrix_A(s, p, n, gamma=1):
    F = galois.GF(p)
    l = optimal_shape(s, n, n, gamma)
    n_i = n + l
    t_i = next_t_i(s, n, n_i, gamma)
    chain = Chain.generate_one_random(p, n, l)
    U = F(chain.create_exhaust_matrix(s))
    D = F(np.random.randint(0, p - 1, size=(t_i, n_i)))
    V = np.dot(U, np.transpose(D))
    V = F(np.concatenate([V, np.ones(shape=(s**n, 1))], axis=1))
    A = F(face_splitting(U, V) % p)
    return A


def generate_random_matrix_without_dimension_constraint(s, p, n, l, t):
    F = galois.GF(p)
    chain = Chain.generate_one_random(p, n, l)
    U = F(chain.create_exhaust_matrix(s))
    D = F(np.random.randint(0, p - 1, size=(t, n + l)))
    V = np.dot(U, np.transpose(D))
    V = F(np.concatenate([V, np.ones(shape=(s**n, 1))], axis=1))
    A = F(face_splitting(U, V) % p)
    return A


######################## Benchmark rank distribution ####################
def sample_for_benchmark_ranks(s, p, n, gamma):
    A = generate_one_random_matrix_A(s, p, n, gamma)
    return np.linalg.matrix_rank(A)


@click.command()
@click.option("--output", required=True)
def full_benchmark_ranks(output, s=2, p=3, n_min=4, n_max=9, iterations=100):
    os.makedirs(output, exist_ok=True)
    for gamma in [1, 1.05, 1.1]:
        results_holder = {}
        for n in range(n_min, n_max + 1):
            print(f"gamma={gamma}, n={n}")
            results_holder[n] = []
            for _ in range(iterations):
                results_holder[n].append(sample_for_benchmark_ranks(s, p, n, gamma))
        with open(
            os.path.join(
                output,
                f"gamma_{gamma}.pickle",
            ),
            "wb",
        ) as f:
            pickle.dump(results_holder, f)


######################### Bechmark Encodings ##############################
def sample_for_benchmark_encoding(s, p, n, n_tries=50, gamma=1):
    field = galois.GF(p)
    counter_pure_success = 0
    counter_success_encoding_switching = 0
    for _ in range(n_tries):
        b = field(np.random.randint(0, s, size=(s**n,)))
        A = generate_one_random_matrix_A(s, p, n, gamma)
        solution, encoding, rank_defect = solve_overdetermined_linear_system(
            A,
            b,
            field,
            Encoding.canonical_encoding(s, p),
            use_encoding_switching=False,
            bypass_rank_drop=True,
        )
        if rank_defect == 0:
            counter_pure_success += 1
            counter_success_encoding_switching += 1
        else:
            solution, encoding = check_rank_drop(A, b, solution, encoding, rank_defect)
            if solution is not None:
                counter_success_encoding_switching += 1
    return counter_pure_success, counter_success_encoding_switching


@click.command()
@click.option("--output", required=True)
def benchmark_encodings(output):
    s, p = 2, 3
    n_min, n_max = 4, 9
    gammas = [1, 1.05, 1.1]
    results = {}
    for gamma in gammas:
        results[gamma] = {}
        for n in range(n_min, n_max + 1):
            a, b = sample_for_benchmark_encoding(s, p, n, gamma=gamma)
            results[gamma][n] = {"pure_successes": a, "successes_encoding_switching": b}
    os.makedirs(output, exist_ok=True)
    with open(
        os.path.join(
            output,
            "data.pickle",
        ),
        "wb",
    ) as f:
        pickle.dump(results, f)


############################## Generation table size #########################################


def generate_table_size_data_for_s(s, n_min, n_max):
    rows = []
    for n in range(n_min, n_max):
        l = optimal_shape(s, n, n)
        t_s = []
        n_i = n + l
        for _ in range(n):
            t_i = next_t_i(s, n, n_i)
            t_s.append(t_i)
            n_i += t_i

        rows.append(
            {
                "s": s,
                "s_plus_1": s + 1,
                "n": n,
                "l": l,
                "t_s": t_s,
                "pbs": l + 2 * sum(t_s),
            }
        )

    return {
        "s": s,
        "n_min": n_min,
        "n_max": n_max,
        "rows": rows,
    }


def generate_all_table_size_data():
    specs = [(2, 4, 15), (4, 2, 8), (16, 2, 5)]
    return {
        "tables": [
            generate_table_size_data_for_s(s, n_min, n_max) for s, n_min, n_max in specs
        ]
    }


def format_table_size_block(data):
    n_max = data["n_max"]
    lines = []

    for row in data["rows"]:
        t_s = row["t_s"]
        padded_t_s = [str(ti) for ti in t_s] + [
            "-" for _ in range(n_max - 1 - row["n"])
        ]
        line = (
            f"{row['s']} & {row['s_plus_1']} & {row['n']} & {row['l']} & "
            + " & ".join(padded_t_s)
            + f" & {row['pbs']}\\\\\n\\hline"
        )
        lines.append(line)

    return "\n".join(lines)


def format_all_table_size(data):
    lines = []

    for table in data["tables"]:
        lines.append(r"\begin")
        lines.append(format_table_size_block(table))

    return "\n".join(lines)


@click.command()
@click.option("--output", "output_path", required=True)
def generate_table_size_data(output_path):
    data = generate_all_table_size_data()
    os.makedirs(output_path, exist_ok=True)
    with open(os.path.join(output_path, "shapes.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@click.command()
@click.option("--input", "input_path", required=True)
@click.option("--output", "output_path", required=True)
def format_table_size(input_path, output_path):
    with open(os.path.join(input_path, "shapes.json"), "r", encoding="utf-8") as f:
        data = json.load(f)

    table = format_all_table_size(data)

    os.makedirs(output_path, exist_ok=True)
    with open(os.path.join(output_path, "Table_1.tex"), "w", encoding="utf-8") as f:
        f.write(table)


########################### Generation table PBS with respect to gamma #############################


def count_pbs_with_respect_to_gamma(s, n, gamma):
    t_s = []
    l = optimal_shape(s, n, n, gamma)
    n_i = n + l
    for _ in range(n):
        t_i = next_t_i(s, n, n_i, gamma)
        t_s.append(t_i)
        n_i += t_i
    count_pbs = l + 2 * sum(t_s)
    return count_pbs


def generate_pbs_gamma_data():
    bounds = {2: (4, 14), 4: (2, 7), 16: (2, 4)}
    gamma_values = [1, 1.05, 1.1]

    data = {}
    for s, (n_min, n_max) in bounds.items():
        rows = []
        for n in range(n_min, n_max + 1):
            row = {
                "n": n,
                "pbs": {
                    str(gamma): count_pbs_with_respect_to_gamma(s, n, gamma)
                    for gamma in gamma_values
                },
            }
            rows.append(row)
        data[str(s)] = {
            "n_min": n_min,
            "n_max": n_max,
            "rows": rows,
        }

    return {
        "bounds": {str(k): list(v) for k, v in bounds.items()},
        "gammas": [str(gamma) for gamma in gamma_values],
        "tables": data,
    }


def format_pbs_gamma_subtable(s, table_data):
    lines = [
        r"\begin{subtable}{\textwidth}",
        r"	\centering",
        r"	\begin{tabular}{|c||c|c|c|}",
        r"		\hline",
        r"		$n$ & \#PBS ($\gamma = 1$) & \#PBS ($\gamma = 1.05$) & \#PBS ($\gamma = 1.1$) \\",
        r"		\hline",
    ]

    for row in table_data["rows"]:
        n = row["n"]
        pbs_1 = row["pbs"]["1"]
        pbs_105 = row["pbs"]["1.05"]
        pbs_11 = row["pbs"]["1.1"]
        lines.append(rf"		{n} & {pbs_1} & {pbs_105} & {pbs_11} \\")
        lines.append(r"		\hline")

    lines.extend(
        [
            r"	\end{tabular}",
            rf"	\caption{{$s={s}$, $p={int(s) + 1}$}}",
            r"\end{subtable}",
        ]
    )
    return "\n".join(lines)


def format_pbs_gamma_table(data):
    lines = [
        r"\begin{table}",
        r"    \centering",
    ]

    for s in ["2", "4", "16"]:
        lines.append(format_pbs_gamma_subtable(s, data["tables"][s]))

    lines.append(r"\end{table}")
    return "\n".join(lines)


@click.command()
@click.option("--output", "output_path", required=True)
def generate_tables_count_pbs_data(output_path):
    data = generate_pbs_gamma_data()
    os.makedirs(output_path, exist_ok=True)
    with open(os.path.join(output_path, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@click.command()
@click.option("--input", "input_path", required=True)
@click.option("--output", "output_path", required=True)
def format_tables_count_pbs(input_path, output_path):
    with open(os.path.join(input_path, "data.json"), "r", encoding="utf-8") as f:
        data = json.load(f)

    latex_table = format_pbs_gamma_table(data)

    os.makedirs(output_path, exist_ok=True)
    with open(os.path.join(output_path, "Table_2.tex"), "w", encoding="utf-8") as f:
        f.write(latex_table)


######## correlation Margin ranks ################


def sample_random_sizes_for_correlation_xp(s, range_n, range_rate_margin):
    n_min, n_max = range_n
    rate_margin_min, rate_margin_max = range_rate_margin
    n = np.random.randint(n_min, n_max + 1)
    margin = rate_margin_min + rate_margin_max * np.random.random()
    n_col = int(round(margin * s**n))
    t = np.random.randint(2, int(floor(sqrt(n_col))))
    l = int(round(n_col / (t + 1)) - n)
    return n, l, t


@click.command()
@click.option("--output", required=True)
def experiment_correlation_margin_rank(
    output, s=2, p=3, range_n=(4, 9), range_rate_margin=(1, 1.15), n_tries=200
):
    results = []
    for _ in range(n_tries):
        n, l, t = sample_random_sizes_for_correlation_xp(s, range_n, range_rate_margin)
        A = generate_random_matrix_without_dimension_constraint(s, p, n, l, t)
        rank = np.linalg.matrix_rank(A)
        results.append([s, p, n, l, t, rank])

    os.makedirs(output, exist_ok=True)
    with open(
        os.path.join(
            output,
            "results.pickle",
        ),
        "wb",
    ) as f:
        pickle.dump(results, f)
