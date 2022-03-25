from parm.api.cursor import Cursor
from parm.api.env import Env
from parm.api.match_result import MatchResult


class Matchable:
    def match(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs) -> Cursor:
        raise NotImplementedError()

    def match_reverse(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs) -> Cursor:
        raise NotImplementedError()
