from typing import Iterable

from parm.api.common import default_match_result
from parm.api.env import Env
from parm.api.asm_cursor import AsmCursor
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

    def match(self, cursors: Iterable[AsmCursor], env: Env, match_result: MatchResult) -> Iterable[AsmCursor]:
        raise NotImplementedError()


class CodeLinePatternBase(LinePattern):
    @property
    def code(self):
        raise NotImplementedError()

    @default_match_result
    def match(self, cursors: Iterable[AsmCursor], env: Env, match_result: MatchResult) -> Iterable[AsmCursor]:
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
    def match(self, cursor: AsmCursor, env: Env, match_result: MatchResult) -> Iterable[AsmCursor]:
        cursors = [cursor]
        for line in self.lines:
            if not cursors:
                raise NoMatches()
            cursors = line.match(cursors, env, match_result)
        return cursors
