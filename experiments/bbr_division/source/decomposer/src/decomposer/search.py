import sys

import click
import numpy as np

from decomposer.chain import Chain
from decomposer.encoding import Encoding

np.set_printoptions(threshold=sys.maxsize)


from decomposer.decomposition import MultiDec
from decomposer.plots.loggers import *
from decomposer.shape_decomposition import next_t_i, optimal_shape
from decomposer.utils.utils import Sbox, face_splitting, generate_settings


#################################Function to generate S-boxes#################################""
def search(s, p, n, gamma=1.1, sbox=None):
    if sbox is None:
        sbox = Sbox.random_sbox(s**n)
    else:
        assert len(sbox.sbox) == s**n
    l = optimal_shape(s, n, n, gamma)  # for now, n = m
    t = next_t_i(s, n, n + l, gamma)
    LOGGER_FLOW.info(f"s={s}, n={n}, lambda={l}, t0={t}")
    settings = generate_settings(n, s, l, t, p, gamma)

    multidec = MultiDec(settings, sbox, Encoding.canonical_encoding(s, p))
    multidec.initialize()

    multidec.run()
    return multidec


def full_search(output, gamma=1.1):
    for s, p, n_min, n_max in [(2, 3, 13, 15), (4, 5, 2, 8), (16, 17, 2, 4)]:
        for n in range(n_min, n_max):
            multidec = search(s, p, n, gamma)
            multidec.write_in_file(p, n, output)


@click.command()
@click.option("--gamma", type=float, required=True)
@click.option("--output", required=True)
def reproduce_search_paper(gamma, output):
    full_search(output, gamma=gamma)


@click.command()
@click.option("--s", type=int, required=True)
@click.option("--p", type=int, required=True)
@click.option("--n", type=int, required=True)
@click.option("--gamma", type=float, default=1.1)
@click.option("--sbox_filename", required=True)
@click.option("--output", required=True)
def search_api(s, p, n, gamma, sbox_filename, output):
    sbox = Sbox.from_file(sbox_filename, s**n)
    multidec = search(s, p, n, gamma, sbox=sbox)
    multidec.write_in_file(p, n, output)
