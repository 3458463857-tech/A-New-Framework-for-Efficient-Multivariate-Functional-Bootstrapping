from math import floor
from random import randint, shuffle, choice, sample

from decomposer.utils.utils import precompute_nonlinear_functions


LINEAR_FUNCTIONS = {
    3 : list(precompute_nonlinear_functions(3)),
    5 : list(precompute_nonlinear_functions(5))
}



class Atomic_Function:
    def __init__(self, p, arity, alphas, psi):
        assert len(alphas) == arity
        self.p = p
        self.arity = arity
        self.alphas = alphas   # Coefficients dans la combinaison linéaire
        assert len(psi) == p
        self.psi = psi        # LUT finale (lol)


    def coeff_of_sparseness(self):
        # count the zeroes in the coefficients
        n_zeroes = sum([int(x == 0) for x in self.alphas])
        return 1 - n_zeroes / self.arity


    def pretty_print(self):
        print(f"Atomic function in the ring Z{self.p} of arity {self.arity}")
        print("Coefficients:")
        print(self.alphas)
        print("Psi:")
        print(self.psi)

    

    def apply(self, inputs):
        assert len(inputs) == self.arity, f"{len(inputs)} vs {self.arity}"
        inputs = [int(x) for x in inputs]
        for xi in inputs:
            assert xi >= 0 and xi < self.p
        return self.psi[sum([alpha_i * x_i for alpha_i, x_i in zip(self.alphas, inputs)]) % self.p]


    def generate_one_random(p, arity):
        # sample an appropriate number of alphas
        alphas = [randint(0, p-1) for _ in range(arity)]
        if p > 5:
            # if p is large enough, the probability iof sampling a random function becomes negligible
            psi = [randint(0, p-1) for _ in range(p)]
        else:
            # sample the function. Make sure it is not a linear function
            psi = choice(LINEAR_FUNCTIONS[p])
                       
        return Atomic_Function(p, arity, alphas, psi)


    def generate_trivial_projection(p, n, index):
        assert index >= 0 and index < n
        return Atomic_Function(p, n, [int(j == index) for j in range(n)], list(range(p)))


    def dummy_one(p, arity):
        # useful for the linear term : function that always return one
        return Atomic_Function(p, arity, [0]*arity, [1]*p)
    
