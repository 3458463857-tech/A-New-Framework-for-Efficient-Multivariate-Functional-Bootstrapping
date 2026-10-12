import os
import pickle

import click


@click.command()
@click.option("--input", required=True)
@click.option("--output", required=True)
def print_table(input, output):
    gammas = [1, 1.05, 1.1]
    with open(os.path.join(input, "data.pickle"), "rb") as f:
        data = pickle.load(f)

    with open(os.path.join(output, "Table_3.tex"), "w") as out:
        out.write(
            "\\begin{table}\n"
            "    \\centering\n"
            "    \\setlength{\\tabcolsep}{4pt}\n"
            "    {\\small\n"
            "    \\begin{tabular}{|c||c|c|c|c|c|c|}\n"
            "        \\hline\n"
            "        \\multirow{2}{*}{$n$} "
            "          & \\multicolumn{2}{c|}{$\\gamma=1$} "
            "          & \\multicolumn{2}{c|}{$\\gamma=1.05$} "
            "          & \\multicolumn{2}{c|}{$\\gamma=1.1$} \\\\\n"
            "        \\cline{2-7}\n"
            "          & \\makecell{Full\\\\rank} & \\makecell{Success\\\\(enc.~switch)} "
            "          & \\makecell{Full\\\\rank} & \\makecell{Success\\\\(enc.~switch)} "
            "          & \\makecell{Full\\\\rank} & \\makecell{Success\\\\(enc.~switch)} \\\\\n"
            "        \\hline\n"
        )

        for n in data[1]:
            row = " & ".join(
                [
                    f"{round(data[gamma][n]['pure_successes'] / 200 * 100)} \\% & "
                    f"{round(data[gamma][n]['successes_encoding_switching'] / 200 * 100)} \\%"
                    for gamma in gammas
                ]
            )
            out.write(f"        {n} & {row} \\\\\n")
            out.write("        \\hline\n")

        out.write("    \\end{tabular}\n    \\end{table}\n")
