from abc import ABC

from parm.api.common import default_match_result
from parm.api.env import Env
from parm.api.cursor import Cursor
from parm.api.exceptions import NoMatches, PatternNotReversible
from parm.api.match_result import MatchResult
from parm.api.matchable import Matchable

from parm.extensions.execution_context import ExecutionContext


class LinePattern:
    @property
    def code(self):
        raise NotImplementedError()

    def match(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs) -> Cursor:
        raise NotImplementedError()


class CodeLineBase:
    @property
    def code(self):
        raise NotImplementedError()

    @property
    def vars(self):
        raise {}

    def _prepare(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs):
        local_env = env.clone()
        local_env.add_globals(**kwargs)
        local_env.add_locals(**self.vars)
        execution_context = ExecutionContext(cursor, match_result)
        registry = local_env.create_extension_registry(execution_context, local_env)
        registry.load_extensions()
        return local_env, execution_context

    def exec(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs):
        local_env, execution_context = self._prepare(cursor, env, match_result, **kwargs)
        local_env.exec(self.code)
        return execution_context

    def eval(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs):
        local_env, execution_context = self._prepare(cursor, env, match_result, **kwargs)
        result = local_env.eval(self.code)
        return result, execution_context


class CodeLineMatchableGenerator(CodeLineBase):
    @property
    def code(self):
        raise NotImplementedError()

    def generate_matchable(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs):
        result, execution_context = self.eval(cursor, env, match_result, **kwargs)
        assert execution_context.cursor is cursor
        return result

    def match(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs) -> Cursor:
        matchable = self.generate_matchable(cursor, env, match_result, **kwargs)
        return matchable.match(cursor, env, match_result, **kwargs)

    def match_reverse(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs) -> Cursor:
        matchable = self.generate_matchable(cursor, env, match_result, **kwargs)
        return matchable.match_reverse(cursor, env, match_result, **kwargs)


class CodeLinePatternBase(LinePattern, CodeLineBase, Matchable, ABC):
    def match_reverse(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs) -> Cursor:
        raise PatternNotReversible()

    @default_match_result
    def match(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs) -> Cursor:
        execution_context = self.exec(cursor, env, match_result, **kwargs)
        return execution_context.cursor


class BlockPattern:
    @property
    def anchor_index(self) -> int:
        raise NotImplementedError()

    @property
    def lines(self):
        raise NotImplementedError()

    @default_match_result
    def match(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs) -> Cursor:
        anchor_ix = self.anchor_index
        if anchor_ix:
            c = cursor.prev()
            for line in reversed(self.lines[:anchor_ix]):
                if not c:
                    raise NoMatches()
                c = line.match_reverse(c, env, match_result, **kwargs)

        c = cursor
        for line in self.lines[anchor_ix:]:
            if not c:
                raise NoMatches()
            c = line.match(c, env, match_result, **kwargs)
        return c
