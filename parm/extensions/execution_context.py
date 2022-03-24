from parm.api.cursor import Cursor
from parm.api.match_result import MatchResult


class ExecutionContext:
    def __init__(self, cursor: Cursor, match_result: MatchResult):
        self.cursor = cursor
        self.match_result = match_result
