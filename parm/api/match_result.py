from __future__ import annotations

from typing import Mapping, Union, List, Iterable
from contextlib import contextmanager

from parm.api.transactions import Transactable
from parm.api.chaining import ChainMap, ChainStack, ChainCounter
from parm.api.exceptions import CaptureCollision, TooManyMatches, NoMatches

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
        self.parent = parent  # type: MatchResult

    @contextmanager
    def transact(self):
        with super().transact():
            self._track_chainstack(self._scopes)
            yield

    def __iter__(self):
        return iter(self._scopes)

    def __getitem__(self, item):
        return self._scopes[item]

    def __len__(self):
        return len(self._scopes)

    def new_scope(self):
        scope = MatchResult(self.parent)
        self._scopes.push(scope)
        return scope

    def to_obj(self):
        return [v.to_obj() for v in self._scopes]

    def to_json(self):
        return obj_to_json(self.to_obj())


class MatchResult(Transactable):
    def __init__(self, parent=None, transaction=None):
        super().__init__(transaction)
        self.parent = parent  # type: MatchResult

        self._scopes = ChainMap()
        self._scope_ix = ChainCounter(-1)
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
        self._add_rollback_op(lambda: self._invalidate_vars(vs))

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
    def subs(self) -> Mapping[_IndexType, List[MatchResult]]:
        return self._subs

    @property
    def sub(self) -> Mapping[_IndexType, MatchResult]:
        return self._sub

    def declare_var(self, name):
        self[name] = DeclaredVar(self, name)

    def __getitem__(self, item):
        try:
            result = self._results[item]
            if isinstance(result, DeclaredVar):
                return result.val
            return result
        except KeyError:
            if self.parent is None:
                raise
            return self.parent[item]

    def __setitem__(self, key, value):
        if key is None:
            return

        if not isinstance(key, str):
            raise ValueError(f"Key must be a string, got {key}!")

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
        assert ix not in self._sub
        assert name not in self._sub
        self._sub[ix] = scope
        self._sub[name] = scope

    def _add_subs(self, ix, name, scope):
        assert isinstance(scope, MultiMatchResult)
        assert ix not in self._subs
        assert name not in self._subs
        self._subs[ix] = scope
        self._subs[name] = scope

    def _add_existing_scope(self, scope, name=None):
        ix = self.add_scope(scope, name)
        self._add_sub(ix, name, scope)

    def new_scope(self, name=None):
        scope = MatchResult(self)
        self._add_existing_scope(scope, name)
        return scope

    def new_temp_scope(self):
        return MatchResult(self)

    def _add_existing_multi_scope(self, scope, name=None):
        ix = self.add_scope(scope, name)
        self._add_subs(ix, name, scope)

    def new_multi_scope(self, name=None) -> MultiMatchResult:
        scope = MultiMatchResult(self)
        self._add_existing_multi_scope(scope, name)
        return scope

    def new_temp_multi_scope(self):
        return MultiMatchResult(self)

    def merge_scope(self, scope):
        assert isinstance(scope, MatchResult)
        assert scope not in self._scopes

        for k, v in scope._results.items():
            self[k] = v

        def _add_mapping(src_map, add_fn):
            sorted_sub = sorted([kv for kv in src_map.items() if isinstance(kv[0], int)], key=lambda kv: kv[0])
            name_rmap = {}
            for name, value in src_map.items():
                if isinstance(name, str):
                    name_rmap[value] = name

            for i, (ix, s) in enumerate(sorted_sub):
                assert i == ix
                name = name_rmap.get(s, None)
                add_fn(s, name)

        _add_mapping(scope._sub, self._add_existing_scope)
        _add_mapping(scope._subs, self._add_existing_multi_scope)

    def merge_multi_scope(self, multi_scope):
        assert isinstance(multi_scope, MultiMatchResult)
        assert multi_scope not in self._scopes

        ss = list(multi_scope)
        if len(ss) > 1:
            raise TooManyMatches()
        if len(ss) == 0:
            raise NoMatches()
        self.merge_scope(ss[0])

    @staticmethod
    def _dict_filter(d):
        r_map = {}
        result = {}
        for k, v in d.items():
            assert isinstance(k, (int, str))
            if v in r_map:
                if isinstance(k, str):
                    old_k = r_map[v]
                    assert isinstance(old_k, int)
                    del result[old_k]
                    result[k] = v
                    r_map[v] = k
            else:
                result[k] = v
                r_map[v] = k
        return result

    def _sub_unique(self):
        return self._dict_filter(self._sub)

    def _subs_unique(self):
        return self._dict_filter(self._subs)

    def to_obj(self):
        result = {}
        result.update(self._results)

        sub_match_objs = {k: v.to_obj() for k, v in self._sub_unique().items()}
        if sub_match_objs:
            result['sub_matches'] = sub_match_objs

        sub_multi_match_objs = {k: v.to_obj() for k, v in self._subs_unique().items()}
        if sub_multi_match_objs:
            result['sub_multi_matches'] = sub_multi_match_objs

        return result

    def to_json(self):
        return obj_to_json(self.to_obj())


def obj_to_json(obj):
    if isinstance(obj, (int, str)):
        return obj
    if isinstance(obj, list):
        return [obj_to_json(e) for e in obj]
    if isinstance(obj, dict):
        return {str(k): obj_to_json(v) for k, v in obj.items()}
    if hasattr(obj, 'to_json'):
        return obj.to_json()
    return str(obj)
