import json


class Encoding:
    def __init__(self, s, p, encoding):
        self.s = s
        self.p = p
        assert set(encoding.keys()) == set(range(s))
        self.encoding = encoding

    def encode(self, x):
        # by default takes the first one
        assert 0 <= x and x < self.s
        return self.encoding[x][0]

    def decode(self, y):
        assert 0 <= y and y < self.p
        for i in range(self.s):
            if y in self.encoding[i]:
                return i
        raise ValueError(
            f"Image value not in the encoding: {y} never attained by {self}"
        )

    # is x \in Zs encoded by y\in Fp
    def is_y_encoding_x(self, x, y):
        assert y < self.p
        assert x < self.s
        return y in self.encoding[x]

    def is_y_busy(self, y):
        assert y < self.p
        for i in range(self.s):
            if y in self.encoding[i]:
                return True
        return False

    def append_y_to_encoding_of_x(self, x, y):
        assert y < self.p
        assert x < self.s
        assert not self.is_y_busy(y)
        self.encoding[x].append(y)

    def equal_under_encoding(self, y1, y2):
        return self.decode(y1) == self.decode(y2)

    def canonical_encoding(s, p):
        return Encoding(s, p, {i: [i] for i in range(s)})

    def __str__(self):
        return json.dumps(self.encoding, indent=2)

    def write_in_file(self, f):
        for i in range(self.s):
            f.write(f"{i} : {' '.join([str(y) for y in self.encoding[i]])}\n")
