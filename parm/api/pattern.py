from typing import Iterable

from parm.api.env import Env
from parm.api.cursor import Cursor
from parm.api.exceptions import NoMatches, PatternMismatchException, TooManyMatches
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
            self._add_skipping_magics,
        ])

    def add_pre_run_hook(self, callback):
        self._pre_run_hooks.append(callback)

    @staticmethod
    def _add_basic_vars(env: Env, cursor: Cursor, match_result: MatchResult):
        env.add_uni_globals(cursor=cursor)
        env.add_uni_globals(result=match_result)

    @staticmethod
    def _add_skipping_magics(env: Env, cursor: Cursor, _: MatchResult):
        env.add_uni_magic('next', lambda: cursor.next())
        env.add_uni_magic('prev', lambda: cursor.prev())

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

    def _prepare_uni_code_env(self, cursor: Cursor, match_result: MatchResult):
        env = self.env.clone()  # We clone so as not to modify the global environment
        self._exec_pre_run_hooks(env, cursor, match_result)
        return env

    def match(self, cursors: Iterable[Cursor], match_result: MatchResult) -> Iterable[Cursor]:
        for c in cursors:
            env = self._prepare_uni_code_env(c, match_result)
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
            ms = match_result.new_multi_scope(name)
            for c in cursors:
                s = ms.new_scope()
                c.match(pattern, s)
        env.add_multi_vars(match_all=_match_all)

        def _match_some(pattern, name=None):
            match_count = 0
            with match_result.transact():
                ms = match_result.new_multi_scope(name)
                for c in cursors:
                    try:
                        with ms.transact():
                            s = ms.new_scope()
                            c.match(pattern, s)
                    except PatternMismatchException:
                        pass
                if match_count <= 0:
                    raise NoMatches()
        env.add_multi_vars(match_some=_match_some)

        def _match_single(pattern, name=None):
            matched = False
            with match_result.transact():
                ms = match_result.new_multi_scope(name)
                for c in cursors:
                    try:
                        with ms.transact():
                            s = ms.new_scope()
                            c.match(pattern, s)
                    except PatternMismatchException:
                        continue
                    if matched:
                        raise TooManyMatches()
                    matched = True
                if not matched:
                    raise NoMatches()
        env.add_multi_vars(match_single=_match_single)

    def _prepare_multi_code_env(self, cursors: Iterable[Cursor], match_result: MatchResult):
        env = self.env.clone()  # We clone so as not to modify the global environment
        self._exec_pre_run_hooks(env, cursors, match_result)
        return env

    def match(self, cursors: Iterable[Cursor], match_result: MatchResult) -> Iterable[Cursor]:
        env = self._prepare_multi_code_env(cursors, match_result)
        result = env.run_multi_code(self.code)
        if result is None:
            result = cursors
        yield from result


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
