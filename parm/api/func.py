from typing import Reversible

from parm.api.cursor import Cursor
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
    def cursors(self) -> Reversible[Cursor]:
        raise NotImplementedError()

    @property
    def start(self) -> Cursor:
        raise NotImplementedError()

    @property
    def end(self) -> Cursor:
        raise NotImplementedError()
