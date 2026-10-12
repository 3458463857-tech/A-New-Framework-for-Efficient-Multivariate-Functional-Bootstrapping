import copy
import time

import galois
import numpy as np

from decomposer.encoding import Encoding
from decomposer.gauss_elimination_rs import gauss_elimination
from decomposer.plots.loggers import *


def gauss_elimination_python(A, b):
    b = np.array(b)
    Ab = np.concatenate((A, b.reshape(-1, 1)), axis=1)

    m, n = A.shape

    h = 0  # Initialization of the pivot row
    k = 0  #  Initialization of the pivot column

    while h < m and k < n:
        #  Find the k-th pivot:
        i_max = h + np.argmax(abs(Ab[h:, k]))
        if Ab[i_max, k] == 0:
            #  No pivot in this column, pass to next column
            k += 1
        else:
            # swap the current row and the one of the pivot
            Ab[[h, i_max]] = Ab[[i_max, h]]

            # normalize the row of the pivot
            Ab[h, :] /= Ab[h, k]
            #  Do for all rows other than pivot:
            for i in range(m):
                if i != h:
                    f = Ab[i, k] / Ab[h, k]
                    #  Fill with zeros the lower part of pivot column:
                    Ab[i, :] -= Ab[h, :] * f
            #  Increase pivot row and column
            h += 1
            k += 1
    return Ab


def find_pivot(row):
    i = 0
    while i < len(row) and not row[i]:
        i += 1
    if i == len(row):
        # ligne nulle => problème
        raise ValueError("Matrice not full rank in the first place")
    else:
        return i, row[i]


def solve_overdetermined_linear_system(
    A, b, field, encoding, use_encoding_switching, bypass_rank_drop=False
):
    m, n = A.shape
    assert m <= n
    assert len(b) == m

    Ab_rust = gauss_elimination(A, b, field.order)

    Ab = field(np.reshape(np.array(Ab_rust), newshape=(m, n + 1)) % field.order)

    A_echelon, b_echelon = Ab[:, :-1], Ab[:, -1]

    solution = [0] * n

    rank_defects = []
    # on lit la solution dans b_echelon, et on remplit dans les indices correspondants aux pivots
    for i, row in enumerate(A_echelon):
        try:
            i_pivot, _ = find_pivot(row)
            solution[i_pivot] = b_echelon[i]
        except ValueError:
            # LOGGER_DECOMP.info("%d/(%d, %d)", i, m, n)
            rank_defects.append(i)

    solution = field(np.array(solution))
    assert solution is not None
    LOGGER_DECOMP.info("%d/(%d, %d)", m - len(rank_defects), m, n)

    if bypass_rank_drop:
        return solution, encoding, len(rank_defects)

    if len(rank_defects) > 0:
        if use_encoding_switching:
            solution, encoding = check_rank_drop(
                A, b, solution, encoding, len(rank_defects)
            )
        else:
            return None, None, len(rank_defects)
    return solution, encoding, len(rank_defects)


def check_rank_drop(A, b, solution, encoding, rank_defect):
    encoding_trial = copy.deepcopy(encoding)
    b_actual = np.dot(A, solution)
    for x, y in zip(b, b_actual):
        x = int(x)
        y = int(y)
        if encoding_trial.is_y_encoding_x(x, y):
            continue
        elif encoding_trial.is_y_busy(y):
            LOGGER_DECOMP.info("Rank drop failed")
            return None, encoding
        else:
            encoding_trial.append_y_to_encoding_of_x(x, y)

    LOGGER_DECOMP.info("Rank drop succeed")
    return solution, encoding_trial
