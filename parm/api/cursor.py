from parm.match_result import MatchResult


class Cursor:
    @property
    def address(self):
        raise NotImplementedError()

    def match(self, pattern) -> MatchResult:
        raise NotImplementedError()

    def next(self):
        """

        :rtype: Cursor
        """
        raise NotImplementedError()
