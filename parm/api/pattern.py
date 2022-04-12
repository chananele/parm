from abc import ABC

from parm.api.program import Program
from parm.api.cursor import Cursor
from parm.api.exceptions import NoMatches, ReverseSearchUnsupported
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

    def match(self, ctx: ExecutionContext, **kwargs) -> ExecutionContext:
        matchable = self.generate_matchable(ctx, **kwargs)
        return matchable.match(ctx, **kwargs)

    def match_reverse(self, ctx: ExecutionContext, **kwargs) -> ExecutionContext:
        matchable = self.generate_matchable(ctx, **kwargs)
        return matchable.match_reverse(ctx, **kwargs)


class CodeLinePatternBase(LinePattern, CodeLineBase, Matchable, ABC):
    def match_reverse(self, ctx: ExecutionContext, **kwargs) -> ExecutionContext:
        raise ReverseSearchUnsupported()

    def match(self, ctx: ExecutionContext, **kwargs) -> ExecutionContext:
        execution_context = self.exec(ctx, **kwargs)
        return execution_context


class BlockPattern:
    @property
    def anchor_index(self) -> int:
        raise NotImplementedError()

    @property
    def lines(self):
        raise NotImplementedError()

    def match(self, ctx: ExecutionContext, **kwargs) -> ExecutionContext:
        anchor_ix = self.anchor_index

        c = ctx
        for line in reversed(self.lines[:anchor_ix]):
            if not c:
                raise NoMatches()
            c = line.match_reverse(c, **kwargs)

        c = ctx
        for line in self.lines[anchor_ix:]:
            if not c:
                raise NoMatches()
            c = line.match(c, **kwargs)
        return c
