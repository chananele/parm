from parm.api.cursor import Cursor
from parm.api.program_base import ProgramBase
from parm.api.match_result import MatchResult


class ExecutionContext:
    def __init__(self, cursor: Cursor, match_result: MatchResult, current_line, program: ProgramBase = None):
        if program is None:
            program = cursor.program

        self.cursor = cursor
        self.match_result = match_result
        self.current_line = current_line
        self.program = program

    @property
    def next_line(self):
        return self.current_line.next_line

    def fork(self, cursor=None, match_result=None, current_line=None):
        if cursor is None:
            cursor = self.cursor
        if match_result is None:
            match_result = self.match_result
        if current_line is None:
            current_line = self.current_line

        return ExecutionContext(cursor=cursor, match_result=match_result, current_line=current_line)

    def advance_instruction(self):
        self.cursor = self.cursor.next()

    def regress_instruction(self):
        self.cursor = self.cursor.prev()

    def fork_next_instruction(self):
        return self.fork(cursor=self.cursor.next())

    def fork_prev_instruction(self):
        return self.fork(cursor=self.cursor.prev())

    def fork_offset(self, offset):
        return self.fork(cursor=self.cursor.get_cursor_by_offset(offset))

    def fork_next_line(self):
        return self.fork(current_line=self.next_line)

    def match(self, **kwargs):
        self.current_line.match(self, **kwargs)


class TerminalPattern:
    @property
    def next_pattern(self):
        raise NotImplementedError()

    def match(self, ctx, **kwargs):
        pass

    def match_reverse(self, ctx, **kwargs):
        pass
