from parm.api.cursor import Cursor
from parm.api.program import Program
from parm.api.match_result import MatchResult


class Matchable:
    def match(self, cursor: Cursor, program: Program, match_result: MatchResult, **kwargs) -> Cursor:
        raise NotImplementedError()

    def match_reverse(self, cursor: Cursor, program: Program, match_result: MatchResult, **kwargs) -> Cursor:
        raise NotImplementedError()
