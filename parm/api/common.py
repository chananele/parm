from typing import Iterable

from parm.api.exceptions import PatternMismatchException, TooManyMatches, NoMatches
from parm.api.match_result import MatchResult
from parm.api.cursor import Cursor


def find_all(pattern, cursors: Iterable[Cursor], match_result: MatchResult = None) -> Iterable[Cursor]:
    if match_result is None:
        match_result = MatchResult()

    for c in cursors:
        try:
            with match_result.transact():
                c.match(pattern)
                yield c
        except PatternMismatchException:
            pass


def find_first(pattern, cursors: Iterable[Cursor], match_result: MatchResult = None) -> Iterable[Cursor]:
    if match_result is None:
        match_result = MatchResult()

    for c in cursors:
        try:
            with match_result.transact():
                c.match(pattern)
                yield c
                return
        except PatternMismatchException:
            pass

    raise NoMatches()


def find_single(pattern, cursors: Iterable[Cursor], match_result: MatchResult = None) -> Iterable[Cursor]:
    if match_result is None:
        match_result = MatchResult()

    match = None
    for c in cursors:
        try:
            with match_result.transact():
                c.match(pattern, match_result)
        except PatternMismatchException:
            continue
        if match is not None:
            raise TooManyMatches()
        match = c
    if match is None:
        raise NoMatches()
    yield match
