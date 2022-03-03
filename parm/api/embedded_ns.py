"""
>>> class AutoInc:
...     def __init__(self):
...         self.v = 0
...     def get_inc(self):
...         self.v += 1
...         return self.v
...     def reset(self):
...         self.v = 0
>>> z = AutoInc()
>>> x = EmbeddedLocalNS()
>>> x.add_magic('i', z.get_inc)
>>> print(x.evaluate('i'))
1
>>> print(x.evaluate('i'))
2
>>> print(x.evaluate('i + i'))
7
>>> print(x.evaluate('i * 2'))
10

>>> x.add_magic('reset', lambda n: n.reset(), z)
>>> print(x.evaluate('i'))
6
>>> x.execute('reset')
>>> print(x.evaluate('i'))
1
"""

from collections.abc import Mapping


class Magic:
    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        return self.callback(*self.args, **self.kwargs)


class EmbeddedLocalNS(Mapping):
    def __init__(self, _magics=None, _vals=None, _globals=None):
        if _magics is None:
            _magics = {}

        if _vals is None:
            _vals = {}

        if _globals is None:
            _globals = {}

        self._magics = _magics
        self._vars = _vals
        self._globals = _globals

    def __len__(self):
        return len(self._magics) + len(self._vars)

    def __iter__(self):
        yield from self._vars
        yield from self._magics

    def clone(self):
        return EmbeddedLocalNS(self._magics.copy(), self._vars.copy(), self._globals.copy())

    def execute(self, code):
        exec(code, self._globals, self)

    def evaluate(self, code):
        return eval(code, self._globals, self)

    def set_global(self, key, value):
        self._globals[key] = value

    def add_global(self, key, value):
        if key in self._globals:
            raise KeyError(f'Global "{key}" already exists!')
        self.set_global(key, value)

    def set_var(self, key, value):
        if key in self._magics:
            raise KeyError(f'Magic "{key}" already exists!')
        self._vars[key] = value

    def add_var(self, key, value):
        if key in self._vars:
            raise KeyError(f'Var "{key}" already exists!')
        self.set_var(key, value)

    def set_magic(self, key, callback, *args, **kwargs):
        if key in self._vars:
            raise KeyError(f'Var "{key}" already exists!')
        self._magics[key] = Magic(callback, *args, **kwargs)

    def add_magic(self, key, callback, *args, **kwargs):
        if key in self._magics:
            raise KeyError(f'Magic "{key}" already exists!')
        self.set_magic(key, callback, *args, **kwargs)

    def del_var(self, key):
        del self._vars[key]

    def del_magic(self, key):
        del self._magics[key]

    def del_key(self, key):
        try:
            self.del_var(key)
        except KeyError:
            self.del_magic(key)

    def __getitem__(self, item):
        try:
            return self._vars[item]
        except KeyError:
            return self._magics[item]()

    def __setitem__(self, key, value):
        if key in self._magics:
            raise SyntaxError(f'The name "{key}" is reserved!')
        self._vars[key] = value

    def __contains__(self, item):
        return item in self._vars or item in self._magics
