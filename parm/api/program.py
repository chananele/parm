from parm.api.exceptions import UnresolvedSymbolException
from parm.api.type_hints import ReversibleIterable

from parm.api.env import Env
from parm.api.match_result import MatchResult
from parm.api.cursor import Cursor
from parm.api.null_cursor import NullCursor
from parm.api.common import find_all, find_first, find_single
from parm.api.program_base import ProgramBase


def _repeat(initial, func, count):
    result = initial
    for _ in range(count):
        result = func(result)
    return result


class Program(ProgramBase):
    def __init__(self, env: Env = None):
        if env is None:
            env = Env.create_default_env()

        self.env = env
        self.register_default_extensions()

    def register_extension_type(self, ext_type):
        self.env.register_extension_type(ext_type)

    def register_default_extensions(self):
        from parm.extensions.default_extensions import DefaultExtension
        self.register_extension_type(DefaultExtension)

    def find_all(self, pattern, match_result: MatchResult):
        if isinstance(pattern, str):
            pattern = self.create_pattern(pattern)

        return find_all(pattern, cursors=self.asm_cursors, match_result=match_result)

    def find_first(self, pattern, match_result: MatchResult):
        if isinstance(pattern, str):
            pattern = self.create_pattern(pattern)

        return find_first(pattern, cursors=self.asm_cursors, match_result=match_result)

    def find_single(self, pattern, match_result: MatchResult):
        if isinstance(pattern, str):
            pattern = self.create_pattern(pattern)

        return find_single(pattern, cursors=self.asm_cursors, match_result=match_result)

    def find_last(self, pattern, match_result):
        if isinstance(pattern, str):
            pattern = self.create_pattern(pattern)

        return find_first(pattern, cursors=reversed(self.asm_cursors), match_result=match_result)

    def create_cursor(self, address) -> Cursor:
        raise NotImplementedError()

    def create_null_cursor(self) -> Cursor:
        return NullCursor(self)

    def match(self, pattern, match_result, **kwargs) -> Cursor:
        if isinstance(pattern, str):
            pattern = self.create_pattern(pattern)

        return self.create_null_cursor().match(pattern, match_result, **kwargs)

    def create_pattern(self, pattern):
        raise NotImplementedError()

    def create_data_stream(self, cursor):
        raise NotImplementedError()

    def find_symbol(self, symbol_name) -> Cursor:
        raise UnresolvedSymbolException(symbol_name)

    @property
    def asm_cursors(self) -> ReversibleIterable[Cursor]:
        raise NotImplementedError()
