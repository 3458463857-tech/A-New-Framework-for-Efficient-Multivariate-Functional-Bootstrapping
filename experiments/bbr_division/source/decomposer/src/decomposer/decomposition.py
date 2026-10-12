import os
from math import ceil

import galois
import numpy as np

from decomposer.chain import Chain
from decomposer.gauss import solve_overdetermined_linear_system
from decomposer.plots.loggers import *
from decomposer.shape_decomposition import next_t_i
from decomposer.utils.parameters import select_and_format_parameters
from decomposer.utils.utils import face_splitting, norm, unpack_settings


class TooMuchIterationsException(Exception):
    pass


BACKTRACK_THRESHOLD = 5
MAX_ITERATIONS = 50


class MultiDec:
    def __init__(self, settings, sbox, encoding):
        self.settings = settings
        self.n, self.s, self.l, self.t, self.p, self.gamma = unpack_settings(settings)[
            1
        ]
        self.field = galois.GF(self.p)
        self.sbox = sbox
        assert self.s**self.n == sbox.len(), f"s={self.s}, n={self.n}, len={sbox.len()}"
        self.t_is = [self.t]
        self.decompositions = []
        self.encoding = encoding

    def initialize(self):
        rank = 0
        counter_failures = 0
        # check if the matrix of the base if full rank. If it not, we might as well restart again.
        while rank < self.n + self.l:
            counter_failures += 1
            self.base_chain = Chain.generate_one_random(self.p, self.n, self.l)
            self.base_matrix = self.field(self.base_chain.create_exhaust_matrix(self.s))
            rank = np.linalg.matrix_rank(self.base_matrix)
            LOGGER_BASE.info("Rank:%d/%d", rank, self.n + self.l)
        LOGGER_BASE.info("#Tries:%d", counter_failures)

    def create_decomposition_i(self, i):
        assert i >= 0 and i < self.n

        settings_decomp = self.settings
        base_matrix_local = np.concatenate(
            [self.base_matrix] + [dec.products for dec in self.decompositions], axis=1
        )
        assert base_matrix_local.shape[0] == self.s**self.n
        assert base_matrix_local.shape[1] == self.n + self.l + sum(self.t_is[:-1]), (
            f"{self.base_matrix.shape[1]} vs {self.n + self.l + sum(self.t_is[:-1])}"
        )

        counter = 0
        n_i = self.n + self.l + sum(self.t_is[:-1])
        dec = Decomposition(
            settings_decomp,
            base_matrix_local,
            n_i,
            self.t_is[-1],
            self.sbox.slice(self.s, self.n, i),
            self.encoding,
        )
        dec.initialize()
        while not dec.check_if_is_solution():
            if i == 0:
                self.initialize()
                base_matrix_local = np.concatenate(
                    [self.base_matrix] + [dec.products for dec in self.decompositions],
                    axis=1,
                )
            dec = Decomposition(
                settings_decomp,
                base_matrix_local,
                n_i,
                self.t_is[-1],
                self.sbox.slice(self.s, self.n, i),
                self.encoding,
            )
            dec.initialize()
            counter += 1
            if counter == MAX_ITERATIONS:
                raise TooMuchIterationsException

        assert all(
            [
                dec.encoding.equal_under_encoding(x, y)
                for (x, y) in zip(np.dot(dec.Ai, dec.betas), dec.sbox_slice)
            ]
        )

        dec.compute_matrix_product()

        # Now we update the basis, and store the current decomposistion and calculate the dimensions of the next iterations
        self.decompositions.append(dec)

        # optim Matthieu: le calcul est légèrement différent
        n_i = self.n + self.l + sum(self.t_is)
        self.t_is.append(next_t_i(self.s, self.n, n_i, self.gamma))

    def run(self):
        i = 0
        backtrack_counters = {}
        while i < self.n:
            LOGGER_FLOW.info(
                "Output %d, cols=%d",
                i,
                self.t_is[-1] * (self.n + self.l + sum(self.t_is[:-1])),
            )
            try:
                self.create_decomposition_i(i)
                i += 1
            except TooMuchIterationsException:
                if i == 0:
                    LOGGER_FLOW.info(
                        f"Did not find a decomposition for the first output in {MAX_ITERATIONS} tries. Keep Trying"
                    )
                    continue
                LOGGER_FLOW.info("BACKTRACK")
                input("BACKTRACK")
                if i not in backtrack_counters:
                    backtrack_counters[i] = 1
                else:
                    backtrack_counters[i] += 1
                self.decompositions.pop()
                self.t_is.pop()
                i -= 1
                while backtrack_counters.get(i + 1, 0) == BACKTRACK_THRESHOLD:
                    backtrack_counters[i + 1] = 0
                    i -= 1
                    self.decompositions.pop()
                    self.t_is.pop()
                    assert len(self.decompositions) == i
                    assert len(self.t_is) == i + 1

        # remove the last t_i as it is useless
        self.t_is = self.t_is[:-1]

    def compute_worst_norm(self):
        worst_norm = 0
        for t_i, dec in zip(self.t_is, self.decompositions):
            assert len(dec.betas) % (t_i + 1) == 0
            size_slice = len(dec.betas) // (t_i + 1)
            for j in range(t_i):
                n = norm(dec.betas[j * size_slice : (j + 1) * size_slice])
                if n > worst_norm:
                    worst_norm = n
                n = norm(dec.D[j])
                if n > worst_norm:
                    worst_norm = n
        for atomic_function in self.base_chain:
            n = norm(atomic_function.alphas)
            if n > worst_norm:
                worst_norm = n
        return worst_norm

    def write_in_file(self, p, n, output_root):
        with open(os.path.join(output_root, f"new_phis_{p}_{n}"), "w") as f:
            f.write("Base:\n")
            for i, atomic_function in enumerate(self.base_chain[self.n :]):
                f.write(f"{i}:\n")
                f.write(" ".join([str(alpha) for alpha in atomic_function.alphas]))
                f.write("\n")
                f.write(" ".join([str(psi_i) for psi_i in atomic_function.psi]))
                f.write("\n")

        with open(os.path.join(output_root, f"d_{p}_{n}"), "w") as f:
            for i, dec in enumerate(self.decompositions):
                f.write(" ".join([str(d_i) for d_i in dec.D.flatten()]))
                f.write("\n")

        with open(os.path.join(output_root, f"betas_{p}_{n}"), "w") as f:
            for i, dec in enumerate(self.decompositions):
                f.write(" ".join([str(beta_i) for beta_i in dec.betas]))
                f.write("\n")

        with open(os.path.join(output_root, f"sbox_{p}_{n}"), "w") as f:
            f.write(" ".join([str(y) for y in self.sbox.sbox]))

        with open(os.path.join(output_root, f"parameters_{p}_{n}"), "w") as f:
            f.write(f"l={self.l}\n")
            f.write(f"t_is={self.t_is}\n")
            closest_norm = select_and_format_parameters(
                self.p, self.compute_worst_norm()
            )
            # f.write(str_params)
            f.write(f"nu={closest_norm}\n")

        with open(os.path.join(output_root, f"encodings_{p}_{n}"), "w") as f:
            for i, dec in enumerate(self.decompositions):
                f.write(f"Decomposition {i}\n")
                dec.encoding.write_in_file(f)


class Decomposition:
    def __init__(self, settings, matrix_basis, n_i, t_i, sbox_slice, encoding):
        # n is the size of the sbox. Ni is the length of the basis
        self.n, self.s, self.l, _, self.p, self.gamma = unpack_settings(settings)[1]
        self.field = galois.GF(self.p)
        self.Ui = matrix_basis
        assert self.Ui.shape == (self.s**self.n, n_i)
        self.n_i = n_i
        self.t_i = t_i
        self.sbox_slice = sbox_slice
        self.encoding = encoding

    def initialize(self):
        # sample the matrix D
        self.D = self.field(np.random.randint(0, 2, size=(self.t_i, self.n_i)))
        self.Vi = np.dot(self.Ui, np.transpose(self.D))
        while np.linalg.matrix_rank(self.Vi) != self.t_i:
            self.D = self.field(np.random.randint(0, 2, size=(self.t_i, self.n_i)))
            self.Vi = np.dot(self.Ui, np.transpose(self.D))
        # append a column of 1 for the linear terms
        self.Vi = np.concatenate(
            [self.Vi, np.ones((self.s**self.n, 1), dtype="uint8")], axis=1
        )

    def check_if_is_solution(self):
        F = galois.GF(self.p)

        self.Ai = F(face_splitting(self.Ui, self.Vi) % self.p)

        sbox = F(self.sbox_slice)

        # A few sanity check
        assert self.Ai.shape[0] == self.s**self.n, (
            f"{self.Ai.shape[0]} == {self.s**self.n}"
        )
        assert len(sbox) == self.s**self.n
        assert self.Ai.shape[1] == (self.t_i + 1) * self.n_i

        assert self.Ai.shape[0] <= self.Ai.shape[1], (
            f"Not a proper shape for matrix A: {self.Ai.shape}. n={self.n},s={self.s},l={self.l},n_i={self.n_i},t_i={self.t_i}"
        )

        # on résout le système sous-determiné avec notre implémentation custom de gauss (et on calcule le rang par la même occasion)
        self.betas, self.encoding, _ = solve_overdetermined_linear_system(
            self.Ai, sbox, galois.GF(self.p), self.encoding, use_encoding_switching=True
        )

        if self.betas is None:
            return False
        return True

    def compute_matrix_product(self):
        assert len(self.betas) == (self.t_i + 1) * self.n_i
        betas_2D = np.reshape(self.betas[: -self.n_i], (self.t_i, self.n_i))
        self.products = np.multiply(
            np.dot(self.Ui, np.transpose(betas_2D)),
            np.dot(self.Ui, np.transpose(self.D)),
        )
