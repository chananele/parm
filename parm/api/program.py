from parm.api.type_hints import ReversibleIterable

from parm.api.env import Env
from parm.api.match_result import MatchResult
from parm.api.cursor import Cursor
from parm.api.common import find_all, find_first, find_single, default_match_result


def _repeat(initial, func, count):
    result = initial
    for _ in range(count):
        result = func(result)
    return result


class Program:

    _post_create_hooks = []

    def __init__(self, env: Env):
        self.env = env
        self._add_generic_injections()
        self._run_post_create_hooks()

    def _add_generic_injections(self):
        self.env.add_uni_fixture('next', lambda cursor: cursor.next())
        self.env.add_uni_fixture('prev', lambda cursor: cursor.prev())

        def skip(count, cursor, set_next_cursor):
            next_cursor = _repeat(cursor, lambda c: c.next(), count)
            set_next_cursor(next_cursor)

        self.env.add_uni_func('skip', skip)

    @classmethod
    def add_post_create_hook(cls, hook):
        cls._post_create_hooks.append(hook)

    def _run_post_create_hooks(self):
        for hook in self._post_create_hooks:
            hook(self)

    @default_match_result
    def find_all(self, pattern, match_result: MatchResult):
        return find_all(pattern, cursors=self.cursors, match_result=match_result)

    @default_match_result
    def find_first(self, pattern, match_result: MatchResult):
        return find_first(pattern, cursors=self.cursors, match_result=match_result)

    @default_match_result
    def find_single(self, pattern, match_result: MatchResult):
        return find_single(pattern, cursors=self.cursors, match_result=match_result)

    @default_match_result
    def find_last(self, pattern, match_result):
        return find_first(pattern, cursors=reversed(self.cursors), match_result=match_result)

    def create_cursor(self, address) -> Cursor:
        raise NotImplementedError()

    def create_pattern(self, pattern):
        raise NotImplementedError()

    def find_symbol(self, symbol_name) -> Cursor:
        raise NotImplementedError()

    @property
    def cursors(self) -> ReversibleIterable[Cursor]:
        raise NotImplementedError()
