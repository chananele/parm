from typing import Reversible

from parm.api.env import Env
from parm.api.cursor import Cursor
from parm.api.common import find_all, find_first, find_single


class Program:
    def __init__(self, env: Env):
        self.env = env
        self.add_env_magics()

    def add_env_magics(self):
        pass

    def find_all(self, pattern):
        find_all(pattern, cursors=self.cursors)

    def find_first(self, pattern):
        find_first(pattern, cursors=self.cursors)

    def find_single(self, pattern):
        find_single(pattern, cursors=self.cursors)

    def find_last(self, pattern):
        return find_first(pattern, cursors=reversed(self.cursors))

    def create_cursor(self, address) -> Cursor:
        raise NotImplementedError()

    @property
    def cursors(self) -> Reversible[Cursor]:
        raise NotImplementedError()
