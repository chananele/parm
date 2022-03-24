from typing import Reversible

from parm.api.asm_cursor import AsmCursor
from parm.api.common import find_first


class Func:
    def __init__(self, env, program):
        self.env = env
        self.program = program

    def find_first(self, pattern):
        return find_first(pattern, cursors=self.cursors)

    def find_last(self, pattern):
        return find_first(pattern, cursors=reversed(self.cursors))

    @property
    def cursors(self) -> Reversible[AsmCursor]:
        raise NotImplementedError()

    @property
    def start(self) -> AsmCursor:
        raise NotImplementedError()

    @property
    def end(self) -> AsmCursor:
        raise NotImplementedError()
