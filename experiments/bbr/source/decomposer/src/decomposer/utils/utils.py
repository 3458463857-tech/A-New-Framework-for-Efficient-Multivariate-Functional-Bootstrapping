from itertools import product
from math import log2, sqrt
from random import shuffle

import numpy as np


def decompose(x, base, length):
    assert x < base**length
    assert abs(log2(base) - int(log2(base))) < 1e-5  # arbitrary threshold
    return [(x >> int(log2(base)) * i) % base for i in range(length)]


# Une opération matricielle utile
def face_splitting(a, b):
    return np.array(
        [np.concatenate([row_a * b for b in row_b]) for row_a, row_b in zip(a, b)]
    )  # https://en.wikipedia.org/wiki/Khatri%E2%80%93Rao_product#/media/File:Face_splitting_product_of_matrices.jpg


# calcule la norme d'un vecteur
def norm(vec):
    return sqrt(sum([int(x) ** 2 for x in vec]))


def precompute_nonlinear_functions(p):
    all_functions = set(product(range(p), repeat=p))
    linear_functions = set(
        [
            tuple([(a * x + b) % p for x in range(p)])
            for a, b in product(range(p), repeat=2)
        ]
    )
    return all_functions.difference(linear_functions)


def generate_settings(n, s, l, t, p, gamma):
    return {"n": n, "s": s, "lambda": l, "t": t, "p": p, "gamma": gamma}


def unpack_settings(settings):
    return list(settings.keys()), list(settings.values())


class Sbox:
    def __init__(self, sbox, modulo):
        self.sbox = sbox
        self.size = len(sbox)
        for x in sbox:
            assert x >= 0 and x < modulo
        self.modulo = modulo
        # modulo is s**m

    def slice(self, s, m, index):
        assert s**m == self.modulo
        assert index >= 0 and index < m
        return np.array([(x >> int(log2(s) * index)) % s for x in self.sbox])

    def len(self):
        return len(self.sbox)

    def random_sbox(modulo):
        sbox = list(range(modulo))
        shuffle(sbox)
        return Sbox(sbox, modulo)

    def from_file(path, modulo):
        # comma separated values,
        with open(path, "r") as f:
            data = f.readlines()
            data = data[0]
        data_list = [int(x) for x in data.strip().split(" ")]
        assert set(data_list) == set(range(modulo))
        return Sbox(data_list, modulo)
