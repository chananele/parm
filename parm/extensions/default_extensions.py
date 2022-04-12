from typing import Iterable, Tuple

from parm.api.execution_context import ExecutionContext
from parm.api.common import find_single
from parm.api.cursor import Cursor
from parm.api.match_result import MatchResult
from parm.api.exceptions import PatternMismatchException
from parm.api.matchable import Matchable
from parm.api.parsing.arm_asm import Address

from parm.extensions.extension_base import ExecutionExtensionBase
from parm.extensions.extension_base import injected_func, magic_getter, magic_setter


class InstructionSkipper(Matchable):
    def __init__(self, ext: ExecutionExtensionBase, skip_count: int):
        self.ext = ext
        self.skip_count = skip_count

    def match(self, ctx: ExecutionContext, **kwargs) -> ExecutionContext:
        assert ctx.cursor is self.ext.cursor
        n = self.skip_count
        for _ in range(n):
            ctx = ctx.fork_next()
        return ctx

    def match_reverse(self, ctx: ExecutionContext, **kwargs) -> ExecutionContext:
        assert ctx.cursor is self.ext.cursor
        n = self.skip_count
        for _ in range(n):
            ctx = ctx.fork_prev()
        return ctx


class DefaultExtension(ExecutionExtensionBase):

    @magic_getter('match_result')
    def get_match_result(self) -> MatchResult:
        return self.match_result

    @magic_getter('cursor')
    def get_cursor(self) -> Cursor:
        return self.cursor

    @magic_setter('cursor')
    def set_cursor(self, cursor: Cursor):
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
        pattern = self.create_pattern(pattern)

        return find_single(pattern, cursors, self.match_result)

    @injected_func
    def match_all(self, cursors: Iterable[Cursor], pattern, name=None, **kwargs):
        pattern = self.create_pattern(pattern)

        ms = self.match_result.new_multi_scope(name)
        for c in cursors:
            mr = ms.new_scope()
            c.match(pattern, mr, **kwargs)

    def search(self, pattern, advance, **kwargs) -> Tuple[ExecutionContext, ExecutionContext]:
        pattern = self.create_pattern(pattern)

        ctx = self.execution_context
        mr = self.match_result
        while True:
            try:
                with mr.transact():
                    pre = ctx
                    post = pattern.match(ctx, **kwargs)
                    return pre, post
            except PatternMismatchException:
                ctx = advance(ctx)

    @injected_func
    def find_next(self, pattern, **kwargs) -> ExecutionContext:
        pre, post = self.search(pattern, lambda ctx: ctx.fork_next(), **kwargs)
        return pre

    @injected_func
    def goto_next(self, pattern, **kwargs):
        self.cursor = self.find_next(pattern, **kwargs).cursor

    @injected_func
    def find_after_next(self, pattern, **kwargs) -> ExecutionContext:
        pre, post = self.search(pattern, lambda ctx: ctx.fork_next(), **kwargs)
        return post

    @injected_func
    def goto_after_next(self, pattern, **kwargs):
        self.cursor = self.find_after_next(pattern, **kwargs).cursor

    @injected_func
    def find_prev(self, pattern, **kwargs) -> ExecutionContext:
        pre, post = self.search(pattern, lambda ctx: ctx.fork_prev(), **kwargs)
        return pre

    @injected_func
    def goto_prev(self, pattern, **kwargs):
        self.cursor = self.find_prev(pattern, **kwargs).cursor

    @injected_func
    def find_before_prev(self, pattern, **kwargs) -> ExecutionContext:
        pre, post = self.search(pattern, lambda ctx: ctx.fork_prev(), **kwargs)
        return post

    @injected_func
    def goto_before_prev(self, pattern, **kwargs):
        self.cursor = self.find_before_prev(pattern, **kwargs).cursor

    @injected_func
    def goto(self, location):
        self.cursor = self.ptr(location)

    @injected_func
    def pat(self, pattern: str):
        return self.create_pattern(pattern)

    @injected_func
    def ptr(self, location):
        if isinstance(location, str):
            try:
                location = self.match_result[location]
            except KeyError:
                location = self.program.find_symbol(location)
        if isinstance(location, Address):
            location = location.address
        if isinstance(location, int):
            location = self.program.create_cursor(location)
        assert isinstance(location, Cursor)
        return location


class AnalysisExtension(ExecutionExtensionBase):
    def get_xrefs_to(self, cursor):
        raise NotImplementedError()

    def get_xrefs_from(self, cursor):
        raise NotImplementedError()
