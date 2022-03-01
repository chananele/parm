from parm.match_result import MatchResult


class BaseEnv:
    def create_cursor(self, ea):
        raise NotImplementedError()

    def match(self, pattern, cursor) -> MatchResult:
        raise NotImplementedError()
