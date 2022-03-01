from typing import List, Iterator

from parm.exceptions import TooManyMatches, NoMatches, PatternMismatchException
from parm.match_result import MatchResult

from parm.api.func import Func
from parm.api.embedded_ns import EmbeddedLocalNS


class Env:
    def __init__(self):
        self._embedded_ns = EmbeddedLocalNS()

    def add_magic(self, name, callback):
        self._embedded_ns.add_magic(name, callback)

    def match(self, pattern, cursor) -> MatchResult:
        return self.find_single(pattern, cursors=[cursor])

    def search(self, pattern, cursors) -> List[MatchResult]:
        raise NotImplementedError()

    def find_all(self, pattern, cursors) -> Iterator[MatchResult]:
        for c in cursors:
            try:
                yield self.match(pattern, c)
            except PatternMismatchException:
                pass

    def find_first(self, pattern, cursors) -> MatchResult:
        for c in cursors:
            try:
                return self.match(pattern, c)
            except PatternMismatchException:
                pass

        raise NoMatches()

    def find_single(self, pattern, cursors) -> MatchResult:
        result = list(self.find_all(pattern, cursors))
        count = len(result)
        if count > 1:
            raise TooManyMatches(result)
        if count == 0:
            raise NoMatches()
        return result[0]
