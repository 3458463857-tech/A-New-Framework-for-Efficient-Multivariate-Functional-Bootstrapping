from decomposer.atomic_function import Atomic_Function

from random import shuffle
import numpy as np
from decomposer.utils.utils import decompose

class Chain:
    def __init__(self, p, n, lambd, chain):
        self.p = p
        self.n = n
        self.lambd = lambd
        assert len(chain) == n + lambd, f"{len(chain)} != {n + lambd}"
        self.chain = chain
   
                                     
    def __getitem__(self, key):
        return self.chain[key]



    
    def pretty_print(self):
        print(f"Atomic chain of basis {self.n} and of length {self.lambd + self.n}:")
        print()
        for i, func in enumerate(self.chain):
            print(f"Function {i}")
            func.pretty_print()
            print()



    def generate_one_random(p, n, lambd):
        # construction of the n first projections
        chain = []
        for index in range(n):
            chain.append(Atomic_Function.generate_trivial_projection(p, n, index))

        # construction of the lambda next random atomic function        
        for index in range(lambd):
            chain.append(Atomic_Function.generate_one_random(p, n+index))

        return Chain(p, n, lambd, chain)

        

        

    def apply(self, inputs):
        assert len(inputs) == self.n
        for xi in inputs:
            assert xi >= 0 and xi < self.p, f"Error for {xi}"
        result = [x for x in inputs] # je préfère faire une deepcopy pour éviter des potentielles embrouilles
        for j in range(self.lambd):
            result.append(self.chain[self.n+j].apply(result))
        return result
    



    def create_exhaust_matrix(self, s):
        return np.array([
            self.apply(decompose(x, s, self.n)) for x in range(s ** self.n)
        ])
    







class ChainParallel:
    def __init__(self, p, n, lambd, chain):
        self.p = p
        self.n = n
        self.lambd = lambd
        assert len(chain) == n + lambd, f"{len(chain)} != {n + lambd}"
        self.chain = chain
   
                                     
    def __getitem__(self, key):
        return self.chain[key]



    
    def pretty_print(self):
        print(f"Atomic chain of basis {self.n} and of length {self.lambd + self.n}:")
        print()
        for i, func in enumerate(self.chain):
            print(f"Function {i}")
            func.pretty_print()
            print()



    def generate_one_random(p, n, lambd):
        # construction of the n first projections
        chain = []
        for index in range(n):
            chain.append(Atomic_Function.generate_trivial_projection(p, n, index))

        # construction of the lambda next random atomic function        
        for index in range(lambd):
            chain.append(Atomic_Function.generate_one_random(p, n))

        return ChainParallel(p, n, lambd, chain)

        

        

    def apply(self, inputs):
        assert len(inputs) == self.n
        for xi in inputs:
            assert xi >= 0 and xi < self.p, f"Error for {xi}"
        result = []
        for j in range(self.lambd):
            result.append(self.chain[self.n+j].apply(inputs))
        return inputs + result
    



    def create_exhaust_matrix(self, s):
        return np.array([
            self.apply(decompose(x, s, self.n)) for x in range(s ** self.n)
        ])
    