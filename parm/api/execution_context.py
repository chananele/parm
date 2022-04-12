from parm.api.cursor import Cursor
from parm.api.program_base import ProgramBase
from parm.api.match_result import MatchResult


class ExecutionContext:
    def __init__(self, cursor: Cursor, match_result: MatchResult, program: ProgramBase = None, exception_handlers=None):
        if exception_handlers is None:
            exception_handlers = []

        if program is None:
            program = cursor.program

        self.cursor = cursor
        self.match_result = match_result
        self.program = program
        self.exception_handlers = exception_handlers

    def fork(self, cursor=None, match_result=None, exception_handlers=None):
        if cursor is None:
            cursor = self.cursor
        if match_result is None:
            match_result = self.match_result
        if exception_handlers is None:
            exception_handlers = []

        exception_handlers = self.exception_handlers + exception_handlers
        return ExecutionContext(cursor, match_result, self.program, exception_handlers)

    def fork_next(self, exception_handlers=None):
        return self.fork(self.cursor.next(), exception_handlers=exception_handlers)

    def fork_prev(self, exception_handlers=None):
        return self.fork(self.cursor.prev(), exception_handlers=exception_handlers)

    def fork_offset(self, offset, exception_handlers=None):
        return self.fork(self.cursor.get_cursor_by_offset(offset), exception_handlers=exception_handlers)
