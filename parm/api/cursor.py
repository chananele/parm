from parm.api.env import Env
from parm.api.match_result import MatchResult
from parm.api.exceptions import NoMoreInstructions
from parm.api.parsing.arm_asm import Instruction


class Cursor:
    def __init__(self, env):
        self.env = env  # type: Env

    @property
    def instruction(self) -> Instruction:
        raise NotImplementedError()

    @property
    def address(self):
        raise NotImplementedError()

    def read_bytes(self, count) -> bytes:
        raise NotImplementedError()

    def get_cursor_by_offset(self, offset):
        """

        :param int offset:
        :return:
        :rtype: Cursor
        """
        raise NotImplementedError()

    def match(self, pattern, match_result: MatchResult = None, **kwargs):
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


class TerminalCursor(Cursor):
    @property
    def address(self):
        raise NotImplementedError()

    @property
    def instruction(self):
        raise NoMoreInstructions()

    def match(self, pattern, match_result: MatchResult = None, **kwargs) -> Cursor:
        raise NoMoreInstructions()

    def next(self):
        raise NoMoreInstructions()

    def prev(self):
        raise NotImplementedError()


class NullCursor(Cursor):
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
        return pattern.match(self, self.env, match_result, **kwargs)
