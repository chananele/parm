from typing import Iterable

from parm.api.common import default_match_result
from parm.api.env import Env
from parm.api.cursor import Cursor
from parm.api.exceptions import NoMatches
from parm.api.match_result import MatchResult

from parm.extensions.extension_base import create_extension_registry
from parm.extensions.execution_context import ExecutionContext


def load_extension_modules():
    from parm.extensions import default_extensions
    return [default_extensions]


load_extension_modules()


class LinePattern:
    @property
    def code(self):
        raise NotImplementedError()

    def match(self, cursors: Iterable[Cursor], env: Env, match_result: MatchResult) -> Iterable[Cursor]:
        raise NotImplementedError()


class CodeLinePatternBase(LinePattern):
    @property
    def code(self):
        raise NotImplementedError()

    @default_match_result
    def match(self, cursors: Iterable[Cursor], env: Env, match_result: MatchResult) -> Iterable[Cursor]:
        next_cursors = []
        for c in cursors:

            local_env = env.clone()
            execution_context = ExecutionContext(c, match_result)
            registry = create_extension_registry(execution_context, local_env)
            registry.load_extensions()
            local_env.run_code(self.code)

            next_cursor = execution_context.cursor
            next_cursors.append(next_cursor)

        return next_cursors


class BlockPattern:
    @property
    def lines(self):
        raise NotImplementedError()

    @default_match_result
    def match(self, cursor: Cursor, env: Env, match_result: MatchResult) -> Iterable[Cursor]:
        cursors = [cursor]
        for line in self.lines:
            if not cursors:
                raise NoMatches()
            cursors = line.match(cursors, env, match_result)
        return cursors
