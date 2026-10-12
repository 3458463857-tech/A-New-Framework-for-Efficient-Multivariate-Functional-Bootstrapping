import json
import os
from math import log2
from pathlib import Path

import click


def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_subtable(s_value, entries):
    rows = []
    for biwidth in sorted(entries, key=lambda x: int(x)):
        timing = entries[biwidth]
        rows.append(f"        {int(biwidth) * int(log2(int(s_value)))} & {timing} \\\\")
        rows.append("\\hline")
    body = "\n".join(rows)

    return f"""\\begin{{subtable}}{{0.3\\textwidth}}
    \\centering
    \\begin{{tabular}}{{|c|c|}}
        \\hline
        \\textbf{{Biwidth}} & \\textbf{{Timing (ms)}} \\\\
        \\hline
{body}
    \\end{{tabular}}
    \\caption{{$s={s_value}$}}
\\end{{subtable}}"""


def json_to_latex_table(data):
    subtables = []
    for s_value in ["3", "5", "17"]:
        if s_value in data:
            subtables.append(make_subtable(s_value, data[s_value]))

    return """\\begin{table}[ht]
    \\centering
%s
    \\caption{Timings in milliseconds by biwidth.}
\\end{table}""" % "\n\\hfill\n".join(subtables)


@click.command()
@click.option("--input", "input", required=True)
@click.option("--output", "output", required=True)
@click.option("--perror", "perror", required=True)
def format_tables(input, output, perror):
    input_path = os.path.join(input, f"timings_hlut-{perror}.json")
    output_path = os.path.join(output, f"Table_{4 if perror == '40' else 5}.tex")

    data = load_data(input_path)
    latex = json_to_latex_table(data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(latex)
