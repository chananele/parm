from contextlib import contextmanager

from parm.api.exceptions import ExpectFailure
from parm.api.embedded_ns import EmbeddedLocalNS


def expect(cond):
    if not cond:
        raise ExpectFailure()


class Env:
    def __init__(self):
        self._uni_ns = EmbeddedLocalNS()
        self._multi_ns = EmbeddedLocalNS()
        self._add_default_injections()

    def add_uni_magic(self, name, callback, *args, **kwargs):
        self._uni_ns.add_magic(name, callback, *args, **kwargs)

    def add_multi_magic(self, name, callback, *args, **kwargs):
        self._multi_ns.add_magic(name, callback, *args, **kwargs)

    def add_common_magic(self, name, callback, *args, **kwargs):
        self.add_uni_magic(name, callback, *args, **kwargs)
        self.add_multi_magic(name, callback, *args, **kwargs)

    def del_uni_var(self, name):
        self._uni_ns.del_var(name)

    def del_multi_var(self, name):
        self._multi_ns.del_var(name)

    def add_uni_var(self, name, value):
        self._uni_ns.add_var(name, value)

    def add_multi_var(self, name, value):
        self._multi_ns.add_var(name, value)

    def add_common_var(self, name, value):
        self.add_uni_var(name, value)
        self.add_multi_var(name, value)

    def _add_default_injections(self):
        self.add_common_var('expect', expect)

    @contextmanager
    def scoped_add_uni_vars(self, **kwargs):
        with self._uni_ns.scoped_add_vars(**kwargs):
            yield

    @contextmanager
    def scoped_add_multi_vars(self, **kwargs):
        with self._multi_ns.scoped_add_vars(**kwargs):
            yield

    def run_uni_code(self, code):
        return self._uni_ns.evaluate(code)

    def run_multi_code(self, code):
        return self._multi_ns.evaluate(code)
