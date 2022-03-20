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
>>> x.add_fixture('i', z.get_inc)
>>> print(x.evaluate('i'))
1
>>> print(x.evaluate('i'))
2
>>> print(x.evaluate('i + i'))
7
>>> print(x.evaluate('i * 2'))
10

>>> x.add_fixture('reset', lambda n: n.reset(), z)
>>> print(x.evaluate('i'))
6
>>> x.execute('reset')
>>> print(x.evaluate('i'))
1
"""

import builtins
from inspect import unwrap
try:
    # Python 3
    from inspect import getfullargspec
except ImportError:
    # Python 2, use inspect.getargspec instead
    # this is the same function really, without support for annotations
    # and keyword-only arguments
    from inspect import getargspec as getfullargspec

from contextlib import contextmanager
from collections.abc import Mapping
from parm.api.chaining import ChainMap


class ResolutionCache:
    def __init__(self):
        self._cache = {}
        self._in_progress = []

    def clear(self):
        self._cache = {}
        self._in_progress = []

    def _mark_in_progress(self, name):
        assert name not in self._in_progress
        assert name not in self._cache
        self._in_progress.append(name)

    def __getitem__(self, item):
        try:
            return self._cache[item]
        except KeyError:
            self._mark_in_progress(item)
            raise

    def __setitem__(self, key, value):
        assert key not in self._cache
        self._in_progress.remove(key)
        self._cache[key] = value


class Fixture:
    def __init__(self, ns, name, callback, *args, **kwargs):
        self.ns = ns  # type: EmbeddedLocalNS
        self.name = name
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        return self.ns.resolve_fixture(self.name)


class EmbeddedLocalNS(Mapping):
    def __init__(self, _fixtures=None, _vals=None, _globals=None):
        if _vals is None:
            _vals = ChainMap()

        if _globals is None:
            _globals = ChainMap()

        if _fixtures is None:
            _fixtures = ChainMap()

        self._fixtures = _fixtures
        self._vars = _vals
        self._globals = _globals

        self._maps = (self._vars, self._globals, self._fixtures)

    @property
    def resolution_cache(self) -> ResolutionCache:
        try:
            # noinspection PyGlobalUndefined
            global _resolution_cache
            return _resolution_cache
        except NameError:
            raise RuntimeError('Must be called from evaluation context!')

    def get_resolved(self, name):
        maps = (self.resolution_cache, self._vars, self._globals)
        for m in maps:
            try:
                return m[name]
            except KeyError:
                pass
        raise KeyError(name)

    def resolve_fixture(self, name):
        try:
            return self.get_resolved(name)
        except KeyError:
            pass

        fixture = self._fixtures[name]
        assert isinstance(fixture, Fixture)
        result = self.call_fixture(fixture)
        self.resolution_cache[name] = result
        return result

    def call_fixture(self, fixture):
        func = fixture.callback
        args = fixture.args
        kwargs = fixture.kwargs

        arg_spec = getfullargspec(unwrap(func))
        for arg_name in arg_spec.args:
            arg_ix = arg_spec.args.index(arg_name)
            try:
                args[arg_ix]
            except IndexError:
                try:
                    kwargs[arg_name]
                except KeyError:
                    arg = self.resolve_fixture(arg_name)
                    kwargs[arg_name] = arg
        return func(*args, **kwargs)

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
        return len(self._fixtures) + len(self._vars)  # Intentionally leave out globals

    def __iter__(self):
        yield from self._vars
        yield from self._globals
        yield from self._fixtures

    def clone(self):
        return EmbeddedLocalNS(self._fixtures.copy(), self._vars.copy(), self._globals.copy())

    def _prepare_embedded_context(self):
        _globals = dict(self._globals)
        exec('import builtins; builtins._resolution_cache = cache', _globals, {'cache': ResolutionCache()})
        assert '__builtins__' in _globals
        assert '_resolution_cache' in _globals['__builtins__']
        return _globals, self

    def execute(self, code):
        _globals, _locals = self._prepare_embedded_context()
        exec(code, _globals, _locals)

    def evaluate(self, code):
        _globals, _locals = self._prepare_embedded_context()
        return eval(code, _globals, _locals)

    def set_global(self, key, value):
        self._globals[key] = value

    def add_global(self, key, value):
        if key in self._globals:
            raise KeyError(f'Global "{key}" already exists!')
        self.set_global(key, value)

    def set_var(self, key, value):
        if key in self._fixtures:
            raise KeyError(f'Fixture "{key}" already exists!')
        self._vars[key] = value

    def add_var(self, key, value):
        if key in self._vars:
            raise KeyError(f'Var "{key}" already exists!')
        self.set_var(key, value)

    def set_fixture(self, key, callback, *args, **kwargs):
        if key in self._vars:
            raise KeyError(f'Var "{key}" already exists!')
        self._fixtures[key] = Fixture(self, key, callback, *args, **kwargs)

    def add_fixture(self, key, callback, *args, **kwargs):
        if key in self._fixtures:
            raise KeyError(f'Fixture "{key}" already exists!')
        self.set_fixture(key, callback, *args, **kwargs)

    def del_var(self, key):
        del self._vars[key]

    def del_fixture(self, key):
        del self._fixtures[key]

    def del_key(self, key):
        try:
            self.del_var(key)
        except KeyError:
            self.del_fixture(key)

    def __getitem__(self, item):
        try:
            return self._vars[item]
        except KeyError:
            fixture = self._fixtures[item]
            return fixture()

    def __setitem__(self, key, value):
        if key in self._fixtures:
            raise SyntaxError(f'The name "{key}" is reserved!')
        self._vars[key] = value

    def __contains__(self, item):
        return item in self._vars or item in self._fixtures

    def __repr__(self):
        return 'EmbeddedLocalNS({!r}, {!r}, {!r})'.format(
            dict(self._fixtures),
            dict(self._vars),
            dict(self._globals))

    def __str__(self):
        return repr(self)
