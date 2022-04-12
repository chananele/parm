from parm.api.cursor import Cursor


class NullCursor(Cursor):
    def read_bytes(self, count) -> bytes:
        raise NotImplementedError()

    def get_cursor_by_offset(self, offset):
        raise NotImplementedError()

    def prev(self):
        raise NotImplementedError()

    def next(self):
        raise NotImplementedError()

    @property
    def address(self):
        raise NotImplementedError()

    @property
    def instruction(self):
        raise NotImplementedError()

    def match(self, pattern, match_result, **kwargs):
        return pattern.match(self, match_result, **kwargs)
