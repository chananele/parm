from typing import Iterator
from parm.api.cursor import Cursor


class Program:
    def create_cursor(self) -> Cursor:
        raise NotImplementedError()

    @property
    def cursors(self) -> Iterator[Cursor]:
        raise NotImplementedError()
