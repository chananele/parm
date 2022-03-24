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
>>> x.add_magic_getter('i', z.get_inc)
>>> print(x.evaluate('i'))
1
>>> print(x.evaluate('i'))
2
>>> print(x.evaluate('i + i'))
7
>>> print(x.evaluate('i * 2'))
10

>>> x.add_magic_getter('reset', lambda n: n.reset(), z)
>>> print(x.evaluate('i'))
6
>>> x.execute('reset')
>>> print(x.evaluate('i'))
1
"""

from contextlib import contextmanager
from collections.abc import Mapping
from parm.api.chaining import ChainMap


class Magic:
    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        return self.callback(*self.args, **self.kwargs)


class EmbeddedLocalNS(Mapping):
    def __init__(self, _magic_getters=None, _magic_setters=None, _locals=None, _globals=None):
        if _locals is None:
            _locals = ChainMap()

        if _globals is None:
            _globals = ChainMap()

        if _magic_getters is None:
            _magic_getters = ChainMap()

        if _magic_setters is None:
            _magic_setters = ChainMap()

        self._magics_getters = _magic_getters
        self._magics_setters = _magic_setters
        self._locals = _locals
        self._globals = _globals

        self._maps = (self._locals, self._globals, self._magics_getters)

    def _take_snapshot(self):
        snapshot = tuple([{} for _ in self._maps])
        for n, m in zip(self._maps, snapshot):
            n.push_map(m)
        return snapshot

    def _restore_snapshot(self, snapshot):
        for n, m in zip(self._maps, snapshot):
            n.pop_map(m)

    @contextmanager
    def snapshot(self):
        snap = self._take_snapshot()
        try:
            yield
        finally:
            self._restore_snapshot(snap)

    def __len__(self):
        return len(self._magics_getters) + len(self._locals)  # Intentionally leave out globals

    def __iter__(self):
        yield from self._locals
        yield from self._magics_getters

    def clone(self):
        return EmbeddedLocalNS(
            _magic_getters=self._magics_getters.copy(),
            _magic_setters=self._magics_setters.copy(),
            _locals=self._locals.copy(),
            _globals=self._globals.copy())

    def _prepare_embedded_context(self, ns=None):
        if ns is not None:
            assert isinstance(ns, dict)
        else:
            ns = {}
        ns.update(self._globals)

        return ns, self

    def execute(self, code, ns=None):
        _globals, _locals = self._prepare_embedded_context(ns)
        exec(code, _globals, _locals)

    def evaluate(self, code, ns=None):
        _globals, _locals = self._prepare_embedded_context(ns)
        return eval(code, _globals, _locals)

    def set_global(self, key, value):
        self._globals[key] = value

    def add_global(self, key, value):
        if key in self._globals:
            raise KeyError(f'Global "{key}" already exists!')
        self.set_global(key, value)

    def set_local(self, key, value):
        if key in self._magics_getters or key in self._magics_setters:
            raise KeyError(f'Magic "{key}" already exists!')
        self._locals[key] = value

    def add_local(self, key, value):
        if key in self._locals:
            raise KeyError(f'Local "{key}" already exists!')
        self.set_local(key, value)

    def set_magic_getter(self, key, callback, *args, **kwargs):
        if key in self._locals:
            raise KeyError(f'Local "{key}" already exists!')
        self._magics_getters[key] = Magic(callback, *args, **kwargs)

    def add_magic_getter(self, key, callback, *args, **kwargs):
        if key in self._magics_getters:
            raise KeyError(f'Magic "{key}" already exists!')
        self.set_magic_getter(key, callback, *args, **kwargs)

    def set_magic_setter(self, key, callback):
        if key in self._locals:
            raise KeyError(f'Local "{key}" already exists!')
        self._magics_setters[key] = callback

    def add_magic_setter(self, key, callback):
        if key in self._magics_setters:
            raise KeyError(f'Magic "{key}" already exists!')
        self.set_magic_setter(key, callback)

    def del_local(self, key):
        del self._locals[key]

    def del_magic_getter(self, key):
        del self._magics_getters[key]

    def del_magic_setter(self, key):
        del self._magics_setters[key]

    def __getitem__(self, item):
        try:
            return self._locals[item]
        except KeyError:
            pass

        magic = self._magics_getters[item]
        return magic()

    def __setitem__(self, key, value):
        try:
            setter = self._magics_setters[key]
        except KeyError:
            if key in self._magics_getters:
                raise AttributeError(f'No setter for "{key}"')
        else:
            return setter(value)

        self._locals[key] = value

    def __contains__(self, item):
        return item in self._locals or item in self._magics_getters

    def __repr__(self):
        return 'EmbeddedLocalNS({!r}, {!r}, {!r}, {!r})'.format(
            dict(self._magics_getters),
            dict(self._magics_setters),
            dict(self._locals),
            dict(self._globals))

    def __str__(self):
        return repr(self)
