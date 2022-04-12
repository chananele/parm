from parm.api.execution_context import ExecutionContext


class Matchable:
    def match(self, ctx: ExecutionContext, **kwargs) -> ExecutionContext:
        raise NotImplementedError()

    def match_reverse(self, ctx: ExecutionContext, **kwargs) -> ExecutionContext:
        raise NotImplementedError()
