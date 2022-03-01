from typing import Iterator

from parm.api.exceptions import PatternMismatchException, TooManyMatches, NoMatches
from parm.api.match_result import MatchResult


def find_all(pattern, cursors) -> Iterator[MatchResult]:
    for c in cursors:
        try:
            yield c.match(pattern)
        except PatternMismatchException:
            pass


def find_first(pattern, cursors) -> MatchResult:
    for c in cursors:
        try:
            return c.match(pattern)
        except PatternMismatchException:
            pass

    raise NoMatches()


def find_single(pattern, cursors) -> MatchResult:
    result = list(find_all(pattern, cursors))
    count = len(result)
    if count > 1:
        raise TooManyMatches(result)
    if count == 0:
        raise NoMatches()
    return result[0]
