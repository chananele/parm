from __future__ import annotations

from parm.api.execution_context import ExecutionContext


class Matchable:
    def match(self, ctx: ExecutionContext, **kwargs):
        raise NotImplementedError()

    def match_reverse(self, ctx: ExecutionContext, **kwargs):
        raise NotImplementedError()
