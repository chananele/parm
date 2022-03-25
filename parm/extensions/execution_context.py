from parm.api.cursor import Cursor
from parm.api.program import Program
from parm.api.match_result import MatchResult


class ExecutionContext:
    def __init__(self, cursor: Cursor, match_result: MatchResult, program: Program):
        self.cursor = cursor
        self.match_result = match_result
        self.program = program
