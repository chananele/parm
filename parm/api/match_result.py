from typing import Mapping, Union, List
from contextlib import contextmanager

from parm.api.exceptions import CaptureCollision, PatternMismatchException

_IndexType = Union[int, str]


class DuplicateValueException(Exception):
    pass


class TrackingDict(dict):
    def __setitem__(self, key, value):
        if key is None:
            return
        try:
            self[key]
        except KeyError:
            super().__setitem__(key, value)
            return
        raise DuplicateValueException()

    def __delitem__(self, key):
        if key is None:
            return
        super().__delitem__(key)


class DeclaredVar:
    def __init__(self, scope, name):
        self.scope = scope  # type: MatchResult
        self.name = name


class UndefinedVar(Exception):
    def __init__(self, var, name):
        self.var = var  # type: DeclaredVar
        self.name = name


class MultiMatchResult:
    def __init__(self, parent=None):
        self._scopes = []
        self._parent = parent  # type: MatchResult

    def __iter__(self):
        return iter(self._scopes)

    def __len__(self):
        return len(self._scopes)

    @contextmanager
    def new_scope(self):
        scope = MatchResult(self._parent)
        self._scopes.append(scope)
        try:
            yield scope
        except PatternMismatchException:
            assert scope is self._scopes.pop(-1)
            scope.invalidate()
            raise


class MatchResult:
    def __init__(self, parent=None):
        self._scopes = {}
        self._results = {}
        self._scope_ix = 0
        self._captured_vars = []  # type: List[DeclaredVar]
        self._parent = parent  # type: MatchResult

        self._subs = TrackingDict()
        self._sub = TrackingDict()

    def invalidate(self):
        for var in self._captured_vars:
            var.scope[var.name] = var

    @property
    def subs(self):
        """
        :rtype: Mapping[_IndexType, List[MatchResult]]
        """
        return self._subs

    @property
    def sub(self):
        """
        :rtype: Mapping[_IndexType, MatchResult]
        """
        return self._subs

    def declare_var(self, name):
        self[name] = DeclaredVar(self, name)

    def __getitem__(self, item):
        try:
            result = self._results[item]
            if isinstance(result, DeclaredVar):
                raise UndefinedVar(result, item)
        except KeyError:
            if self._parent is None:
                raise
            return self._parent[item]

    def __setitem__(self, key, value):
        try:
            existing = self[key]
            if existing != value:
                raise CaptureCollision(key, existing, value)
        except KeyError:
            self._results[key] = value
        except UndefinedVar as uv:
            var = uv.var
            var.scope[key] = value
            self._captured_vars.append(var)

    @contextmanager
    def add_scope(self, scope, name=None):
        ix = self._scope_ix
        self._scope_ix = ix + 1
        self._scopes[ix] = scope
        if name is not None:
            self._scopes[name] = scope
        try:
            yield ix
        except PatternMismatchException:
            if name is not None:
                del self._scopes[name]
            del self._scopes[ix]
            self._scope_ix = ix
            raise

    def _add_sub(self, ix, name, scope):
        assert isinstance(scope, MatchResult)
        self._sub[ix] = scope
        self._sub[name] = scope
        try:
            yield
        except PatternMismatchException:
            del self._sub[ix]
            del self._sub[name]

    def _add_subs(self, ix, name, scope):
        assert isinstance(scope, MultiMatchResult)
        self._subs[ix] = scope
        self._subs[name] = scope
        try:
            yield
        except PatternMismatchException:
            del self._subs[ix]
            del self._subs[name]

    @contextmanager
    def new_scope(self, name=None):
        scope = MatchResult(self)
        try:
            with self.add_scope(scope, name) as ix:
                with self._add_sub(ix, name, scope):
                    yield scope
        except PatternMismatchException:
            scope.invalidate()
            del scope
            raise

    @contextmanager
    def new_multi_scope(self, name=None):
        scope = MultiMatchResult(self)
        try:
            with self.add_scope(scope, name) as ix:
                with self._add_subs(ix, name, scope):
                    yield scope
        except PatternMismatchException:
            del scope
            raise
