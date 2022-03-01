"""
>>> class AutoInc:
...     def __init__(self):
...         self.v = 0
...     def get_inc(self):
...         self.v += 1
...         return self.v
>>> z = AutoInc()
>>> x = EmbeddedLocalNS()
>>> x.set_magic('i', z.get_inc)
>>> print(x.evaluate('i'))
1
>>> print(x.evaluate('i'))
2
>>> print(x.evaluate('i + i'))
7
>>> print(x.evaluate('i * 2'))
10
"""

from collections.abc import Mapping


class EmbeddedLocalNS(Mapping):
    def __init__(self, magics=None, vals=None):
        if magics is None:
            magics = {}

        if vals is None:
            vals = {}

        self._magics = magics
        self._vals = vals

    def __len__(self):
        return len(self._magics) + len(self._vals)

    def __iter__(self):
        for v in self._vals:
            yield v
        for m in self._magics:
            yield m()

    def clone(self):
        return EmbeddedLocalNS(self._magics, self._vals)

    def execute(self, code, _globals=None):
        exec(code, _globals, self.clone())

    def evaluate(self, code, _globals=None):
        return eval(code, _globals, self.clone())

    def set_magic(self, key, callback):
        assert key not in self._vals
        self._magics[key] = callback

    def __getitem__(self, item):
        try:
            return self._vals[item]
        except KeyError:
            return self._magics[item]()

    def __setitem__(self, key, value):
        if key in self._magics:
            raise SyntaxError(f'The name "{key}" is reserved!')
        self._vals[key] = value
