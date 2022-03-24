from typing import Iterable

from parm.api.asm_cursor import AsmCursor
from parm.api.common import find_single

from parm.extensions.extension_base import ExecutionExtensionBase, injected, register_extension, magic_getter


@register_extension
class DefaultExtension(ExecutionExtensionBase):

    @injected
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

    @injected
    def find_single(self, cursors: Iterable[AsmCursor], pattern):
        return find_single(pattern, cursors, self.match_result)
