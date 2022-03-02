from typing import Iterator

from parm.api.match_result import MatchResult


class Cursor:
    def __init__(self, env):
        self.env = env

    @property
    def address(self):
        raise NotImplementedError()

    def match(self, pattern) -> Iterator[MatchResult]:
        raise NotImplementedError()

    def match_single(self, pattern) -> MatchResult:
        raise NotImplementedError()

    def next(self):
        """

        :rtype: Cursor
        """
        raise NotImplementedError()
