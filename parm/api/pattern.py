from typing import Iterator

from parm.api.cursor import Cursor
from parm.api.exceptions import NoMatches
from parm.api.match_result import MatchResult


class LinePattern:
    def match(self, cursors: Iterator[Cursor], match_result: MatchResult) -> Iterator[Cursor]:
        raise NotImplementedError()


class LineUniPattern(LinePattern):
    def __init__(self, env, code):
        self.env = env
        self.code = code

    def match(self, cursors: Iterator[Cursor], match_result: MatchResult) -> Iterator[Cursor]:
        for c in cursors:
            result = self.env.run_uni_code(self.code, c, match_result)
            if result is None:
                result = [c]
            yield from result


class LineMultiPattern(LinePattern):
    def __init__(self, env, code):
        self.env = env
        self.code = code

    def match(self, cursors: Iterator[Cursor], match_result: MatchResult) -> Iterator[Cursor]:
        result = self.env.run_multi_code(self.code, cursors, match_result)
        if result is None:
            result = cursors
        yield from result


class LineAssemblyPattern(LinePattern):
    def __init__(self, env, asm_pat):
        self.env = env
        self.asm_pat = asm_pat

    def match(self, cursors: Iterator[Cursor], match_result: MatchResult) -> Iterator[Cursor]:
        for c in cursors:
            self.asm_pat.match(c, match_result)
            yield c.next()


def check_cursor_list(it: Iterator[Cursor]):
    try:
        f = next(it)
    except StopIteration:
        raise NoMatches()
    yield f
    yield from it


class Pattern:
    def __init__(self, env, lines):
        self.env = env
        self.lines = lines  # type: Iterator[LinePattern]

    def match(self, cursors: Iterator[Cursor], match_result: MatchResult = None):
        if match_result is None:
            match_result = MatchResult()
        for line in self.lines:
            cursors = line.match(cursors, match_result)
            cursors = check_cursor_list(cursors)  # Fail if no cursors left
