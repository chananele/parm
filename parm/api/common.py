from typing import Iterable
from functools import wraps

from inspect import unwrap
try:
    # Python 3
    from inspect import getfullargspec
except ImportError:
    # Python 2, use inspect.getargspec instead
    # this is the same function really, without support for annotations
    # and keyword-only arguments
    from inspect import getargspec as getfullargspec

from parm.api.exceptions import PatternMismatchException, TooManyMatches, NoMatches
from parm.api.match_result import MatchResult
from parm.api.env import Env
from parm.api.cursor import Cursor


def default_initialize(arg_name, initializer):
    def decorator(f):
        arg_spec = getfullargspec(unwrap(f))
        arg_index = arg_spec.args.index(arg_name)

        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                value = args[arg_index]
            except IndexError:
                try:
                    value = kwargs[arg_name]
                except KeyError:
                    value = None
                if value is None:
                    kwargs[arg_name] = initializer()
            else:
                if value is None:
                    args = list(args)
                    args[arg_index] = initializer()
            return f(*args, **kwargs)

        return wrapper

    return decorator


default_match_result = default_initialize('match_result', MatchResult)
default_env = default_initialize('env', Env.create_default_env)


def find_all(pattern, cursors: Iterable[Cursor], match_result: MatchResult, **kwargs) -> Iterable[Cursor]:
    ms = match_result.new_multi_scope()
    for c in cursors:
        scope = ms.new_scope()
        with scope.transact():
            try:
                with scope.transact():
                    c.match(pattern, scope, **kwargs)
                    yield c
            except PatternMismatchException:
                pass


@default_match_result
def find_first(pattern, cursors: Iterable[Cursor], match_result: MatchResult, **kwargs) -> Cursor:
    for c in cursors:
        try:
            with match_result.transact():
                c.match(pattern, match_result, **kwargs)
                return c
        except PatternMismatchException:
            pass
    raise NoMatches()


def find_single(pattern, cursors: Iterable[Cursor], match_result: MatchResult, **kwargs) -> Cursor:
    ms = match_result.new_temp_multi_scope()
    match = None
    for c in cursors:
        try:
            with ms.transact():
                scope = ms.new_scope()
                c.match(pattern, scope, **kwargs)
        except PatternMismatchException:
            continue
        if match is not None:
            raise TooManyMatches()
        match = c
    if match is None:
        raise NoMatches()
    match_result.merge_multi_scope(ms)
    return match
