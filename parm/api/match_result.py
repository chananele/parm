from typing import Mapping, Union, List, Iterable
from contextlib import contextmanager

from parm.api.transactions import Transactable
from parm.api.chaining import ChainMap, ChainStack, ChainCounter
from parm.api.exceptions import CaptureCollision

_IndexType = Union[int, str]


class DuplicateValueException(Exception):
    pass


class TrackingDict(ChainMap):
    """
    A ChainMap that does not allow overwriting values.
    """

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
        self._val = None

    @property
    def val(self):
        if self._val is None:
            raise UndefinedVar(self, self.name)
        return self._val

    @val.setter
    def val(self, val):
        if self._val is not None and val is not None:
            raise DuplicateValueException()
        self._val = val

    def unset_val(self):
        self._val = None

    def is_val_set(self):
        return self._val is None


class UndefinedVar(Exception):
    def __init__(self, var, name):
        self.var = var  # type: DeclaredVar
        self.name = name


class MultiMatchResult(Transactable):
    def __init__(self, parent=None, transaction=None):
        super().__init__(transaction)

        self._scopes = ChainStack()
        self._parent = parent  # type: MatchResult

    @contextmanager
    def transact(self):
        with super().transact():
            self._track_chainstack(self._scopes)
            yield

    def __iter__(self):
        return iter(self._scopes)

    def __len__(self):
        return len(self._scopes)

    def new_scope(self):
        scope = MatchResult(self._parent)
        self._scopes.push(scope)
        return scope


class MatchResult(Transactable):
    def __init__(self, parent=None, transaction=None):
        super().__init__(transaction)
        self._parent = parent  # type: MatchResult

        self._scopes = ChainMap()
        self._scope_ix = ChainCounter()
        self._captured_vars = ChainStack()

        self._subs = TrackingDict()
        self._sub = TrackingDict()

        self._results = ChainMap()

    @staticmethod
    def _invalidate_vars(vs: Iterable[DeclaredVar]):
        for v in vs:
            v.val = None

    def _track_captured_vars(self):
        vs = self._track_chainstack(self._captured_vars)
        self._add_rollback_op(self._invalidate_vars(vs))

    @contextmanager
    def transact(self):
        with super().transact():
            self._track_chaincounter(self._scope_ix)
            self._track_chainmap(self._scopes)
            self._track_chainmap(self._results)
            self._track_chainmap(self._subs)
            self._track_chainmap(self._sub)
            self._track_captured_vars()
            yield

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
                return result.val
            return result
        except KeyError:
            if self._parent is None:
                raise
            return self._parent[item]

    def __setitem__(self, key, value):
        if key is None:
            return

        assert isinstance(key, str)

        try:
            existing = self[key]
            if existing != value:
                raise CaptureCollision(key, existing, value)
        except KeyError:
            self._results[key] = value
        except UndefinedVar as uv:
            var = uv.var
            var.val = value
            self._captured_vars.push(var)

    def add_scope(self, scope, name=None):
        ix = self._scope_ix.inc()
        self._scopes[ix] = scope
        if name is not None:
            self._scopes[name] = scope
        return ix

    def _add_sub(self, ix, name, scope):
        assert isinstance(scope, MatchResult)
        self._sub[ix] = scope
        self._sub[name] = scope

    def _add_subs(self, ix, name, scope):
        assert isinstance(scope, MultiMatchResult)
        self._subs[ix] = scope
        self._subs[name] = scope

    def new_scope(self, name=None):
        scope = MatchResult(self)
        ix = self.add_scope(scope, name)
        self._add_sub(ix, name, scope)
        return scope

    def new_multi_scope(self, name=None) -> MultiMatchResult:
        scope = MultiMatchResult(self)
        ix = self.add_scope(scope, name)
        self._add_subs(ix, name, scope)
        return scope
