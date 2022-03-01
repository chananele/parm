from typing import Reversible
from parm.api import cursor


class Func:
    def __init__(self, env, program):
        self.env = env
        self.program = program
        self.add_env_magics()

    def add_env_magics(self):
        pass

    def find_first(self, pattern):
        return self.env.find_first(pattern, cursors=self.cursors)

    def find_last(self, pattern):
        return self.env.find_first(pattern, cursors=reversed(self.cursors))

    @property
    def cursors(self) -> Reversible[cursor.Cursor]:
        raise NotImplementedError()

    @property
    def start(self) -> cursor.Cursor:
        raise NotImplementedError()

    @property
    def end(self) -> cursor.Cursor:
        raise NotImplementedError()
