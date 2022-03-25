from typing import Iterable

from parm.api.cursor import Cursor
from parm.api.common import find_single
from parm.api.program import Program
from parm.api.exceptions import PatternMismatchException
from parm.api.match_result import MatchResult
from parm.api.matchable import Matchable
from parm.api.parsing.arm_asm import Address

from parm.extensions.extension_base import ExecutionExtensionBase
from parm.extensions.extension_base import injected_func, magic_getter, magic_setter


class InstructionSkipper(Matchable):
    def __init__(self, ext: ExecutionExtensionBase, skip_count: int):
        self.ext = ext
        self.skip_count = skip_count

    def match(self, cursor: Cursor, program: Program, match_result: MatchResult, **kwargs) -> Cursor:
        assert cursor is self.ext.cursor
        n = self.skip_count
        for _ in range(n):
            cursor = cursor.next()
        return cursor

    def match_reverse(self, cursor: Cursor, program: Program, match_result: MatchResult, **kwargs) -> Cursor:
        assert cursor is self.ext.cursor
        n = self.skip_count
        for _ in range(n):
            cursor = cursor.prev()
        return cursor


class DefaultExtension(ExecutionExtensionBase):

    @magic_getter('match_result')
    def get_match_result(self):
        return self.match_result

    @magic_getter('cursor')
    def get_cursor(self):
        return self.cursor

    @magic_setter('cursor')
    def set_cursor(self, cursor):
        self.cursor = cursor

    @injected_func
    def skip_instructions(self, n):
        return InstructionSkipper(self, n)

    @magic_getter
    def next_instruction(self):
        return self.cursor.next()

    @magic_getter
    def prev_instruction(self):
        return self.cursor.prev()

    @injected_func
    def find_single(self, cursors: Iterable[Cursor], pattern):
        return find_single(pattern, cursors, self.match_result)

    @injected_func
    def match_all(self, cursors: Iterable[Cursor], pattern, name=None, **kwargs):
        ms = self.match_result.new_multi_scope(name)
        for c in cursors:
            mr = ms.new_scope()
            c.match(pattern, mr, **kwargs)

    def search(self, pattern, advance, **kwargs):
        cursor = self.cursor
        mr = self.match_result
        while True:
            try:
                with mr.transact():
                    cursor.match(pattern, mr, **kwargs)
                    return cursor
            except PatternMismatchException:
                cursor = advance(cursor)

    @injected_func
    def find_next(self, pattern, **kwargs):
        return self.search(pattern, lambda c: c.next(), **kwargs)

    @injected_func
    def goto_next(self, pattern, **kwargs):
        self.cursor = self.find_next(pattern, **kwargs)

    @injected_func
    def find_prev(self, pattern, **kwargs):
        return self.search(pattern, lambda c: c.prev(), **kwargs)

    @injected_func
    def goto_prev(self, pattern, **kwargs):
        self.cursor = self.find_prev(pattern, **kwargs)

    @injected_func
    def goto(self, location):
        if isinstance(location, str):
            try:
                location = self.match_result[location]
            except KeyError:
                location = self.program.find_symbol(location)
        if isinstance(location, Address):
            location = location.address
        assert isinstance(location, int)
        return self.program.create_cursor(location)


class AnalysisExtension(ExecutionExtensionBase):
    def get_xrefs_to(self, cursor):
        raise NotImplementedError()

    def get_xrefs_from(self, cursor):
        raise NotImplementedError()
