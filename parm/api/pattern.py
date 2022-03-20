from typing import Iterable

from parm.api.env import Env
from parm.api.cursor import Cursor
from parm.api.exceptions import NoMatches, PatternMismatchException, TooManyMatches, ExpectFailure
from parm.api.match_result import MatchResult


class LinePattern:
    def match(self, cursors: Iterable[Cursor], match_result: MatchResult) -> Iterable[Cursor]:
        raise NotImplementedError()


class LineUniPattern(LinePattern):

    def __init__(self, env, code):
        self.env = env
        self.code = code

        self._pre_run_hooks = []
        self._add_default_pre_run_hooks()

    def _add_default_pre_run_hooks(self):
        self._pre_run_hooks.extend([
            self._add_basic_vars,
            self._add_skipping_fixtures,
        ])

    def add_pre_run_hook(self, callback):
        self._pre_run_hooks.append(callback)

    @staticmethod
    def _add_basic_vars(env: Env, cursor: Cursor, match_result: MatchResult):
        env.add_uni_globals(cursor=cursor)
        env.add_uni_globals(result=match_result)

    @staticmethod
    def _add_skipping_fixtures(env: Env, cursor: Cursor, _: MatchResult):
        env.add_uni_fixture('next', lambda: cursor.next())
        env.add_uni_fixture('prev', lambda: cursor.prev())

        def skip(count):
            c = cursor
            for _ in range(count):
                c = c.next()
            return c
        env.add_uni_vars(skip=skip)

        def skip_up_to(count):
            c = cursor
            for _ in range(count):
                c = c.next()
                yield c
        env.add_uni_vars(skip_up_to=skip_up_to)

    def _exec_pre_run_hooks(self, env: Env, cursor: Cursor, match_result: MatchResult):
        for hook in self._pre_run_hooks:
            hook(env, cursor, match_result)

    def match(self, cursors: Iterable[Cursor], match_result: MatchResult) -> Iterable[Cursor]:
        for c in cursors:
            env = c.env
            with env.snapshot():
                self._exec_pre_run_hooks(env, c, match_result)
                result = env.run_uni_code(self.code)
                if result is None:
                    result = [c]
                yield from result


class LineMultiPattern(LinePattern):
    def __init__(self, env, code):
        self.env = env
        self.code = code

        self._pre_run_hooks = []

    def _add_default_pre_run_hooks(self):
        self._pre_run_hooks.extend([
            self._add_basic_vars,
            self._add_pattern_match_cbs,
            self._add_util_cbs,
        ])

    def add_pre_run_hook(self, callback):
        self._pre_run_hooks.append(callback)

    def _exec_pre_run_hooks(self, env: Env, cursors: Iterable[Cursor], match_result: MatchResult):
        for hook in self._pre_run_hooks:
            hook(env, cursors, match_result)

    @staticmethod
    def _add_basic_vars(env: Env, cursors: Iterable[Cursor], match_result: MatchResult):
        env.add_multi_globals(cursors=cursors)
        env.add_multi_globals(result=match_result)

    @staticmethod
    def _add_pattern_match_cbs(env: Env, cursors: Iterable[Cursor], match_result: MatchResult):
        def _match_all(pattern, name=None):
            result = []
            ms = match_result.new_multi_scope(name)
            for c in cursors:
                s = ms.new_scope()
                result.extend(c.match(pattern, s))
        env.add_multi_vars(match_all=_match_all)

        def _match_some(pattern, name=None):
            result = []
            ms = match_result.new_multi_scope(name)
            for c in cursors:
                try:
                    with ms.transact():
                        s = ms.new_scope()
                        result.extend(c.match(pattern, s))
                except PatternMismatchException:
                    pass
            return result
        env.add_multi_vars(match_some=_match_some)

        def _match_single(pattern, name=None):
            result = []
            ms = match_result.new_multi_scope(name)
            for c in cursors:
                try:
                    with ms.transact():
                        s = ms.new_scope()
                        result.extend(c.match(pattern, s))
                except PatternMismatchException:
                    continue
                if result:
                    raise TooManyMatches()
            return result
        env.add_multi_vars(match_single=_match_single)

    @staticmethod
    def _add_util_cbs(env: Env, cursors: Iterable[Cursor], match_result: MatchResult):
        def _single():
            s = None
            for c in cursors:
                if s is not None:
                    raise ExpectFailure()
                s = c
            return [s]

        def _multiple():
            cnt = 0
            first = None
            for c in cursors:
                if cnt == 0:
                    first = c
                else:
                    if cnt == 1:
                        yield first
                    yield c
                cnt += 1
            if cnt <= 1:
                raise NoMatches()

        env.add_multi_fixture('single', _single)
        env.add_multi_fixture('multiple', _multiple)

    def match(self, cursors: Iterable[Cursor], match_result: MatchResult) -> Iterable[Cursor]:
        env = self.env
        with env.snapshot():
            self._exec_pre_run_hooks(env, cursors, match_result)
            result = env.run_multi_code(self.code)
            if not result:
                raise NoMatches()
            return result


class LineAssemblyPattern(LinePattern):
    def __init__(self, env, asm_pat):
        self.env = env
        self.asm_pat = asm_pat

    def match(self, cursors: Iterable[Cursor], match_result: MatchResult) -> Iterable[Cursor]:
        for c in cursors:
            self.asm_pat.match(c, match_result)
            yield c.next()


def check_cursor_list(it: Iterable[Cursor]) -> Iterable[Cursor]:
    for i in it:
        yield i
    else:
        raise NoMatches()


class Pattern:
    def __init__(self, env, lines):
        self.env = env
        self.lines = lines  # type: Iterable[LinePattern]

    def match(self, cursors: Iterable[Cursor], match_result: MatchResult = None):
        if match_result is None:
            match_result = MatchResult()
        for line in self.lines:
            cursors = line.match(cursors, match_result)
            cursors = check_cursor_list(cursors)  # Fail if no cursors left
