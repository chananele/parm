from typing import Iterator
from contextlib import ExitStack, contextmanager

from parm.api.env import Env
from parm.api.cursor import Cursor
from parm.api.exceptions import NoMatches, PatternMismatchException, TooManyMatches
from parm.api.match_result import MatchResult


class LinePattern:
    def match(self, cursors: Iterator[Cursor], match_result: MatchResult) -> Iterator[Cursor]:
        raise NotImplementedError()


class LineUniPattern(LinePattern):
    def __init__(self, env, code):
        self.env = env
        self.code = code

    def match(self, cursors: Iterator[Cursor], match_result: MatchResult) -> Iterator[Cursor]:
        for c in cursors:
            with self.env.scoped_add_uni_vars(cursor=c, results=match_result):
                result = self.env.run_uni_code(self.code)
            if result is None:
                result = [c]
            yield from result


class LineMultiPattern(LinePattern):

    _pre_run_hooks = []

    def __init__(self, env, code):
        self.env = env
        self.code = code

    @classmethod
    def add_pre_run_hook(cls, callback):
        cls._pre_run_hooks.append(callback)

    def _exec_pre_run_hooks(self, es: ExitStack, cursors: Iterator[Cursor], match_result: MatchResult):
        for hook in self._pre_run_hooks:
            hook(es, self.env, cursors, match_result)

    @staticmethod
    def _add_basic_vars(es: ExitStack, env: Env, cursors: Iterator[Cursor], match_result: MatchResult):
        es.enter_context(env.scoped_add_multi_vars(cursors=cursors))
        es.enter_context(env.scoped_add_multi_vars(result=match_result))

    @staticmethod
    def _add_pattern_match_cbs(es: ExitStack, env: Env, cursors: Iterator[Cursor], match_result: MatchResult):
        def _match_all(pattern, name=None):
            with match_result.new_multi_scope(name) as scope:
                for c in cursors:
                    with scope.new_scope() as results:
                        c.match(pattern, results)
        es.enter_context(env.scoped_add_multi_vars(match_all=_match_all))

        def _match_some(pattern, name=None):
            match_count = 0
            with match_result.new_multi_scope(name) as scope:
                for c in cursors:
                    try:
                        with scope.new_scope() as results:
                            c.match(pattern, results)
                    except PatternMismatchException:
                        pass
                if match_count <= 0:
                    raise NoMatches()
        es.enter_context(env.scoped_add_multi_vars(match_some=_match_some))

        def _match_single(pattern, name=None):
            matched = False
            with match_result.new_multi_scope(name) as scope:
                for c in cursors:
                    try:
                        with scope.new_scope() as results:
                            c.match(pattern, results)
                    except PatternMismatchException:
                        continue
                    if matched:
                        raise TooManyMatches()
                    matched = True
                if not matched:
                    raise NoMatches()
        es.enter_context(env.scoped_add_multi_vars(match_single=_match_single))

    @contextmanager
    def _prepare_multi_code_env(self, cursors: Iterator[Cursor], match_result: MatchResult):
        with ExitStack() as es:
            self._exec_pre_run_hooks(es, cursors, match_result)
            yield

    def match(self, cursors: Iterator[Cursor], match_result: MatchResult) -> Iterator[Cursor]:
        with self._prepare_multi_code_env(cursors, match_result):
            result = self.env.run_multi_code(self.code)
        if result is None:
            result = cursors
        yield from result

    _pre_run_hooks.extend([
        _add_basic_vars,
        _add_pattern_match_cbs,
    ])


class LineAssemblyPattern(LinePattern):
    def __init__(self, env, asm_pat):
        self.env = env
        self.asm_pat = asm_pat

    def match(self, cursors: Iterator[Cursor], match_result: MatchResult) -> Iterator[Cursor]:
        for c in cursors:
            self.asm_pat.match(c, match_result)
            yield c.next()


def check_cursor_list(it: Iterator[Cursor]):
    try:
        f = next(it)
    except StopIteration:
        raise NoMatches()
    yield f
    yield from it


class Pattern:
    def __init__(self, env, lines):
        self.env = env
        self.lines = lines  # type: Iterator[LinePattern]

    def match(self, cursors: Iterator[Cursor], match_result: MatchResult = None):
        if match_result is None:
            match_result = MatchResult()
        for line in self.lines:
            cursors = line.match(cursors, match_result)
            cursors = check_cursor_list(cursors)  # Fail if no cursors left
