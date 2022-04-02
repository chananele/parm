from parm.api.match_result import MatchResult
from parm.api.parsing.arm_asm import Instruction


class Cursor:
    def __init__(self, program):
        self.program = program

    @property
    def instruction(self) -> Instruction:
        raise NotImplementedError()

    @property
    def address(self):
        raise NotImplementedError()

    def read_bytes(self, count) -> bytes:
        raise NotImplementedError()

    def create_stream(self):
        return self.program.create_stream(self)

    def get_cursor_by_offset(self, offset: int):
        """

        :param offset:
        :return:
        :rtype: Cursor
        """
        raise NotImplementedError()

    def match(self, pattern, match_result: MatchResult, **kwargs):
        """

        :param pattern:
        :param match_result:
        :param kwargs:
        :return:
        :rtype: Cursor
        """
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


class NullCursor(Cursor):
    def read_bytes(self, count) -> bytes:
        raise NotImplementedError()

    def get_cursor_by_offset(self, offset):
        raise NotImplementedError()

    def prev(self):
        raise NotImplementedError()

    def next(self):
        raise NotImplementedError()

    @property
    def address(self):
        raise NotImplementedError()

    @property
    def instruction(self):
        raise NotImplementedError()

    def match(self, pattern, match_result: MatchResult = None, **kwargs) -> Cursor:
        return pattern.match(self, self.program, match_result, **kwargs)
