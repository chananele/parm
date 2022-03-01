from typing import Iterator
from parm.api import cursor


class Func:
    @property
    def cursors(self) -> Iterator[cursor.Cursor]:
        raise NotImplementedError()

    @property
    def start(self) -> cursor.Cursor:
        raise NotImplementedError()

    @property
    def end(self) -> cursor.Cursor:
        raise NotImplementedError()
