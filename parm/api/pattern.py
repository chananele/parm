from typing import Iterable

from parm.api.common import default_match_result
from parm.api.env import Env
from parm.api.cursor import Cursor
from parm.api.exceptions import NoMatches
from parm.api.match_result import MatchResult

from parm.extensions.execution_context import ExecutionContext


class LinePattern:
    @property
    def code(self):
        raise NotImplementedError()

    def match(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs) -> Cursor:
        raise NotImplementedError()


class CodeLinePatternBase(LinePattern):
    @property
    def code(self):
        raise NotImplementedError()

    @property
    def vars(self):
        raise {}

    @default_match_result
    def match(self, cursor: Cursor, env: Env, match_result: MatchResult, **kwargs) -> Cursor:
        local_env = env.clone()
        local_env.add_globals(**kwargs)
        local_env.add_locals(**self.vars)
        execution_context = ExecutionContext(cursor, match_result)
        registry = local_env.create_extension_registry(execution_context, local_env)
        registry.load_extensions()
        local_env.exec(self.code)
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
            for line in self.lines[:anchor_ix]:
                if not c:
                    raise NoMatches()
                c = line.match_reverse(c, env, match_result, **kwargs)

        c = cursor
        for line in self.lines[anchor_ix:]:
            if not c:
                raise NoMatches()
            c = line.match(c, env, match_result, **kwargs)
        return c
