from typing import Iterator

from parm.api.asm_cursor import AsmCursor
from parm.programs.snippet import ArmSnippetProgram


class CapstoneProgram(ArmSnippetProgram):
    def __init__(self, code: str = "", autoanalyze: bool = False):
        super().__init__()

        self.autoanalyze = autoanalyze
        if code:
            self.add_code_block(code)
        self.add_env_fixtures()

    def _analyze(self, cursors):
        for cursor in cursors:
            # TODO: do stuff and update class methods
            pass

    def analyze(self):
        self._analyze(self._cursors)

    def add_code_block(self, add_code_block):
        before = len(self._cursors)
        super().add_code_block(add_code_block)
        after = len(self._cursors)
        if self.autoanalyze:
            self._analyze(self._cursors[before:after])

    def get_xrefs_to(self, cursor) -> Iterator[AsmCursor]:
        raise NotImplementedError()

    def add_env_fixtures(self):
        self.env.inject_magic_getter('xrefs_to', self.get_xrefs_to)

def capstone_create_program(code: str) -> CapstoneProgram:
    return CapstoneProgram(code)
