from parm.api.asm_cursor import AsmCursor
from parm.api.match_result import MatchResult


class ExecutionContext:
    def __init__(self, cursor: AsmCursor, match_result: MatchResult):
        self.cursor = cursor
        self.match_result = match_result
