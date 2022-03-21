from pathlib import Path
from typing import IO, Iterator, Union

from parm.api.asm_cursor import AsmCursor
from parm.programs.snippet import ArmSnippetProgram

from capstone import CS_ARCH_ARM, CS_ARCH_X86, CS_MODE_ARM, Cs, CsError

CAPSTONE_ARCH = {
    "arm": CS_ARCH_ARM,
    "x86": CS_ARCH_X86,  # Not supported yet
}


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


def disassemble_binary_file(
        binary_path: Path,
        arch: str,
        mode: int,
        offset: int = 0,
        size: Union[int, None] = None) -> Union[bytes, bool]:
    with binary_path.open('rb') as bf:
        binary_file.seek(offset)
        ops = binary_file.read(size)

    if not ops:
        print("Nothing to disassemble ?")
        return False

    # TODO: get capstone mode according to arch-mode
    try:
        md = Cs(CAPSTONE_ARCH[arch], CS_MODE_ARM)
        if not (dis := md.disasm(ops, offset)):
            return False
        return "\n".join(f"0x{inst.address:x}: {inst.mnemonic} {inst.op_str}"
                         for inst in dis)
    except CsError as e:
        print(
            f"Failed initiating capstone for arch: {(CAPSTONE_ARCH[arch], CS_MODE_ARM)} with: {str(e)}"
        )
        return False


def capstone_create_program(code: str) -> CapstoneProgram:
    return CapstoneProgram(code)
