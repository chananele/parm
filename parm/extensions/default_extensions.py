from typing import Iterable

from parm.api.asm_cursor import AsmCursor
from parm.api.common import find_single

from parm.extensions.extension_base import ExecutionExtensionBase
from parm.extensions.extension_base import injected_func, magic_getter, magic_setter


class DefaultExtension(ExecutionExtensionBase):

    @magic_getter('match_result')
    def get_match_result(self):
        return self.match_result

    @magic_getter('cursor')
    def get_cursor(self):
        return self.cursor

    @magic_setter('cursor')
    def set_cursor(self, cursor):
        self.cursor = cursor

    @injected_func
    def skip_instructions(self, n):
        c = self.cursor
        for _ in range(n):
            c = c.next()
        self.cursor = c

    @magic_getter
    def next_instruction(self):
        return self.cursor.next()

    @magic_getter
    def prev_instruction(self):
        return self.cursor.prev()

    @injected_func
    def find_single(self, cursors: Iterable[AsmCursor], pattern):
        return find_single(pattern, cursors, self.match_result)

    @injected_func
    def match_all(self, cursors: Iterable[AsmCursor], pattern, name=None, **kwargs):
        ms = self.match_result.new_multi_scope(name)
        for c in cursors:
            mr = ms.new_scope()
            c.match(pattern, mr, **kwargs)


class AnalysisExtension(ExecutionExtensionBase):
    def get_xrefs_to(self, cursor):
        raise NotImplementedError()

    def get_xrefs_from(self, cursor):
        raise NotImplementedError()
