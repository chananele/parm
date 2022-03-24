from parm.api.env import Env
from parm.api.match_result import MatchResult
from parm.api.exceptions import NoMoreInstructions
from parm.api.parsing.arm_asm import Instruction


class AsmCursor:
    def __init__(self, env):
        self.env = env  # type: Env

    @property
    def instruction(self) -> Instruction:
        raise NotImplementedError()

    @property
    def address(self):
        raise NotImplementedError()

    def match(self, pattern, match_result: MatchResult = None, **kwargs) -> MatchResult:
        raise NotImplementedError()

    def next(self):
        """

        :rtype: AsmCursor
        """
        raise NotImplementedError()

    def prev(self):
        """

        :rtype: AsmCursor
        """
        raise NotImplementedError()


class TerminalAsmCursor(AsmCursor):
    @property
    def address(self):
        raise NotImplementedError()

    @property
    def instruction(self):
        raise NoMoreInstructions()

    def match(self, pattern, match_result: MatchResult = None, **kwargs) -> MatchResult:
        raise NoMoreInstructions()

    def next(self):
        raise NoMoreInstructions()

    def prev(self):
        raise NotImplementedError()


class NullCursor(AsmCursor):
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

    def match(self, pattern, match_result: MatchResult = None, **kwargs) -> MatchResult:
        return pattern.match(self, self.env, match_result, **kwargs)
