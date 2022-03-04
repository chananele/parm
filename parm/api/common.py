from parm.api.exceptions import PatternMismatchException, TooManyMatches, NoMatches
from parm.api.match_result import MatchResult


def find_all(pattern, cursors, match_result: MatchResult = None) -> MatchResult:
    if match_result is None:
        match_result = MatchResult()

    for c in cursors:
        try:
            with match_result.transact():
                yield c.match(pattern)
        except PatternMismatchException:
            pass


def find_first(pattern, cursors, match_result: MatchResult = None) -> MatchResult:
    if match_result is None:
        match_result = MatchResult()

    for c in cursors:
        try:
            with match_result.transact():
                return c.match(pattern)
        except PatternMismatchException:
            pass

    raise NoMatches()


def find_single(pattern, cursors, match_result: MatchResult = None) -> MatchResult:
    if match_result is None:
        match_result = MatchResult()

    result = list(find_all(pattern, cursors))
    count = len(result)
    if count > 1:
        raise TooManyMatches()
    if count == 0:
        raise NoMatches()
    return result[0]
