from parm.api.match_result import MatchResult


class Cursor:
    def __init__(self, env):
        self.env = env

    @property
    def line(self):
        raise NotImplementedError()

    @property
    def address(self):
        raise NotImplementedError()

    def match(self, pattern, match_results: MatchResult = None) -> MatchResult:
        raise NotImplementedError()

    def next(self):
        """

        :rtype: Cursor
        """
        raise NotImplementedError()

    def prev(self):
        """

        :rtype: Cursor
        """
        raise NotImplementedError()
