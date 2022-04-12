from parm.api.type_hints import ReversibleIterable
from parm.api.cursor import Cursor


class ProgramBase:
    def create_cursor(self, address) -> Cursor:
        raise NotImplementedError()

    def create_pattern(self, pattern):
        raise NotImplementedError()

    def create_data_stream(self, cursor):
        raise NotImplementedError()

    def find_symbol(self, symbol_name) -> Cursor:
        raise NotImplementedError()

    @property
    def asm_cursors(self) -> ReversibleIterable[Cursor]:
        raise NotImplementedError()
