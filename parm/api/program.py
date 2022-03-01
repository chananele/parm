from typing import Reversible

from parm.api.env import Env
from parm.api.cursor import Cursor


class Program:
    def __init__(self, env: Env):
        self.env = env
        self.add_env_magics()

    def add_env_magics(self):
        pass

    def find_all(self, pattern):
        self.env.find_all(pattern, cursors=self.cursors)

    def find_first(self, pattern):
        self.env.find_first(pattern, cursors=self.cursors)

    def find_single(self, pattern):
        self.env.find_single(pattern, cursors=self.cursors)

    def find_last(self, pattern):
        return self.env.find_first(pattern, cursors=reversed(self.cursors))

    def create_cursor(self, address) -> Cursor:
        raise NotImplementedError()

    @property
    def cursors(self) -> Reversible[Cursor]:
        raise NotImplementedError()
