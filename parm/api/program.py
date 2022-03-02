from typing import Reversible

from parm.api.env import Env
from parm.api.cursor import Cursor
from parm.api.common import find_all, find_first, find_single


class Program:

    _post_create_hooks = []

    def __init__(self, env: Env):
        self.env = env

    @classmethod
    def add_post_create_hook(cls, hook):
        cls._post_create_hooks.append(hook)

    def _run_post_create_hooks(self):
        for hook in self._post_create_hooks:
            hook(self)

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

    def find_symbol(self, symbol_name) -> Cursor:
        raise NotImplementedError()

    @property
    def cursors(self) -> Reversible[Cursor]:
        raise NotImplementedError()
