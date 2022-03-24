from parm.api.type_hints import ReversibleIterable

from parm.api.env import Env
from parm.api.match_result import MatchResult
from parm.api.asm_cursor import AsmCursor
from parm.api.common import find_all, find_first, find_single, default_match_result


def _repeat(initial, func, count):
    result = initial
    for _ in range(count):
        result = func(result)
    return result


class Program:
    def __init__(self, env: Env):
        self.env = env

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

    def create_cursor(self, address) -> AsmCursor:
        raise NotImplementedError()

    def create_pattern(self, pattern):
        raise NotImplementedError()

    def find_symbol(self, symbol_name) -> AsmCursor:
        raise NotImplementedError()

    @property
    def cursors(self) -> ReversibleIterable[AsmCursor]:
        raise NotImplementedError()
