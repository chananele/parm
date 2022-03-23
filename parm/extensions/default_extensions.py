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
