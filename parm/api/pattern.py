from abc import ABC

from parm.api.program import Program
from parm.api.cursor import Cursor
from parm.api.exceptions import ReverseSearchUnsupported
from parm.api.match_result import MatchResult
from parm.api.matchable import Matchable

from parm.api.execution_context import ExecutionContext


class LinePattern:
    @property
    def code(self):
        raise NotImplementedError()

    def match(self, cursor: Cursor, program: Program, match_result: MatchResult, **kwargs) -> Cursor:
        raise NotImplementedError()


class CodeLineBase:
    @property
    def code(self):
        raise NotImplementedError()

    @property
    def vars(self):
        raise {}

    def _prepare(self, ctx: ExecutionContext, **kwargs):
        new_ctx = ctx.fork()
        program = new_ctx.program
        env = program.env
        local_env = env.clone()
        local_env.add_globals(**kwargs)
        local_env.add_locals(**self.vars)
        registry = local_env.create_extension_registry(new_ctx, local_env)
        registry.load_extensions()
        return local_env, new_ctx

    def exec(self, ctx: ExecutionContext, **kwargs):
        local_env, execution_context = self._prepare(ctx, **kwargs)
        local_env.exec(self.code)
        return execution_context

    def eval(self, ctx: ExecutionContext, **kwargs):
        local_env, execution_context = self._prepare(ctx, **kwargs)
        result = local_env.eval(self.code)
        return result, execution_context


class CodeLineMatchableGenerator(CodeLineBase):
    @property
    def code(self):
        raise NotImplementedError()

    def generate_matchable(self, ctx: ExecutionContext, **kwargs):
        result, new_ctx = self.eval(ctx, **kwargs)
        assert new_ctx.cursor is ctx.cursor
        return result

    def match(self, ctx: ExecutionContext, **kwargs):
        matchable = self.generate_matchable(ctx, **kwargs)
        matchable.match(ctx, **kwargs)

    def match_reverse(self, ctx: ExecutionContext, **kwargs):
        matchable = self.generate_matchable(ctx, **kwargs)
        matchable.match_reverse(ctx, **kwargs)


class CodeLinePatternBase(LinePattern, CodeLineBase, Matchable, ABC):
    def match_reverse(self, ctx: ExecutionContext, **kwargs):
        raise ReverseSearchUnsupported()

    def match(self, ctx: ExecutionContext, **kwargs):
        new_ctx = self.exec(ctx, **kwargs)
        new_ctx.current_line = ctx.next_line
        new_ctx.match(**kwargs)


class ForwardLineBase:
    @property
    def next_line(self):
        raise NotImplementedError()

    def match(self, ctx: ExecutionContext, **kwargs):
        raise NotImplementedError()


class BackwardLineBase:
    @property
    def next_line(self):
        raise NotImplementedError()

    def match(self, ctx: ExecutionContext, **kwargs):
        raise NotImplementedError()


class TerminalForwardLine(ForwardLineBase):
    @property
    def next_line(self):
        raise NotImplementedError()

    def match(self, ctx: ExecutionContext, **kwargs):
        pass


class ForwardLine(ForwardLineBase):
    def __init__(self, line, next_line):
        self.line = line
        self._next_line = next_line

    @property
    def next_line(self):
        return self._next_line

    def match(self, ctx: ExecutionContext, **kwargs):
        return self.line.match(ctx, **kwargs)


class TerminalBackwardLine(BackwardLineBase):
    @property
    def next_line(self):
        return NotImplementedError()

    def match(self, ctx: ExecutionContext, **kwargs):
        pass


class BackwardLine(BackwardLineBase):
    def __init__(self, line, prev_line):
        self.line = line
        self._prev_line = prev_line

    @property
    def next_line(self):
        return self._prev_line

    def match(self, ctx: ExecutionContext, **kwargs):
        return self.line.match_reverse(ctx, **kwargs)


class BlockPattern:
    def __init__(self, lines, anchor_index):
        self.lines = lines
        self.anchor_index = anchor_index
        self.b_line, self.f_line = self._link_lines()

    def relink_lines(self):
        self.b_line, self.f_line = self._link_lines()

    def _link_lines(self):

        anchor_ix = self.anchor_index

        b_line = TerminalBackwardLine()
        for line in self.lines[:anchor_ix]:
            b_line = BackwardLine(line, b_line)

        f_line = TerminalForwardLine()
        for line in reversed(self.lines[anchor_ix:]):
            f_line = ForwardLine(line, f_line)

        return b_line, f_line

    def match(self, cursor: Cursor, match_result: MatchResult, **kwargs):
        ctx = ExecutionContext(cursor, match_result, current_line=self.b_line)
        ctx.match(**kwargs)
        ctx = ExecutionContext(cursor, match_result, current_line=self.f_line)
        ctx.match(**kwargs)
