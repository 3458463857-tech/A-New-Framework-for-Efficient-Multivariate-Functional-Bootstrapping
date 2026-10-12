from math import ceil, sqrt


def next_t_i(s, n, n_i, gamma=1.0):
    t_i = ceil(gamma * s**n / n_i - 1)
    return max(t_i, 1)  # avoid the awkward case where t_i = 0


def optimal_shape(s, n, m, gamma=1.0):
    lowest_cost = float("inf")
    best_lambda = 0
    for l in range(1, s**n):
        t_is = []
        n_i = n + l
        for _ in range(m):
            t_i = next_t_i(s, n, n_i, gamma)
            if t_i == n_i:
                l += 1
            t_is.append(t_i)
            n_i += t_i
        cost = l + 2 * sum(t_is)
        if cost < lowest_cost:
            lowest_cost = cost
            best_lambda = l
    return best_lambda
