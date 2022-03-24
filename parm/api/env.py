from contextlib import contextmanager

from parm.api.exceptions import ExpectFailure
from parm.api.embedded_ns import EmbeddedLocalNS

from parm.extensions.injection_context import InjectionContext


def expect(cond):
    if not cond:
        raise ExpectFailure()


class Env(InjectionContext):
    def __init__(self, ns):
        self._ns = ns  # type: EmbeddedLocalNS

    @contextmanager
    def snapshot(self):
        with self._ns.snapshot():
            yield

    @classmethod
    def create_default_env(cls):
        env = cls(EmbeddedLocalNS())
        env._add_default_injections()
        return env

    def _add_default_injections(self):
        self.add_global('expect', expect)

    def clone(self):
        return Env(self._ns.clone())

    def inject_magic_getter(self, name, callback, *args, **kwargs):
        self._ns.add_magic_getter(name, callback, *args, **kwargs)

    def inject_magic_setter(self, name, callback):
        self._ns.add_magic_setter(name, callback)

    def inject_global(self, name, value):
        self.add_global(name, value)

    def inject_local(self, name, value):
        self.add_local(name, value)

    def del_local(self, name):
        self._ns.del_local(name)

    def add_local(self, name, value):
        self._ns.add_local(name, value)

    def add_locals(self, **kwargs):
        for k, v in kwargs.items():
            self.add_local(k, v)

    def add_global(self, name, value):
        self._ns.add_global(name, value)

    def add_globals(self, **kwargs):
        for k, v in kwargs.items():
            self.add_global(k, v)

    def eval(self, code, ns=None):
        return self._ns.evaluate(code, ns)

    def exec(self, code, ns=None):
        return self._ns.execute(code, ns)
