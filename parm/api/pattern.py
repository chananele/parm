from typing import Iterable

from parm.api.common import default_match_result
from parm.api.env import Env
from parm.api.cursor import Cursor
from parm.api.exceptions import NoMatches, PatternMismatchException, TooManyMatches, ExpectFailure
from parm.api.match_result import MatchResult


class LinePattern:
    @property
    def code(self):
        raise NotImplementedError()

    def match(self, cursors: Iterable[Cursor], env: Env, match_result: MatchResult) -> Iterable[Cursor]:
        raise NotImplementedError()


class LineUniPattern(LinePattern):
    @property
    def code(self):
        raise NotImplementedError()

    @default_match_result
    def match(self, cursors: Iterable[Cursor], env: Env, match_result: MatchResult) -> Iterable[Cursor]:
        next_cursors = []
        for c in cursors:
            with env.snapshot():
                env.add_uni_globals(cursor=c, match_result=match_result)
                result = env.run_uni_code(self.code)
                next_cursors.extend(result)
        return next_cursors


class LineMultiPattern(LinePattern):
    @property
    def code(self):
        raise NotImplementedError()

    @default_match_result
    def match(self, cursors: Iterable[Cursor], env: Env, match_result: MatchResult) -> Iterable[Cursor]:
        with env.snapshot():
            env.add_multi_globals(match_result=match_result, cursors=cursors)
            return env.run_multi_code(self.code)


class BlockPattern:
    @property
    def lines(self):
        raise NotImplementedError()

    @default_match_result
    def match(self, cursor: Cursor, env: Env, match_result: MatchResult) -> Iterable[Cursor]:
        cursors = [cursor]
        for line in self.lines:
            if not cursors:
                raise NoMatches()
            cursors = line.match(cursors, env, match_result)
        return cursors
