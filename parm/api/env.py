from typing import List

from parm.exceptions import TooManyMatches, NoMatches
from parm.match_result import MatchResult
from parm.api.embedded_ns import EmbeddedLocalNS


class Env:
    def __init__(self, program):
        self.program = program
        self._embedded_ns = EmbeddedLocalNS()

    def create_cursor(self, ea):
        raise NotImplementedError()

    def match(self, pattern, cursor) -> MatchResult:
        return self.find_single(pattern, cursors=[cursor])

    def search(self, pattern, cursors) -> List[MatchResult]:
        raise NotImplementedError()

    def find_all(self, pattern, cursors=None) -> List[MatchResult]:
        if cursors is None:
            cursors = self.program.cursors
        return self.search(pattern, cursors)

    def find_single(self, pattern, cursors) -> MatchResult:
        result = self.find_all(pattern, cursors)
        count = len(result)
        if count > 1:
            raise TooManyMatches(result)
        if count == 0:
            raise NoMatches()
        return result[0]
