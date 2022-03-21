from pathlib import Path
from typing import IO, Iterator, Tuple, Union

from elftools.elf.elffile import ELFError, ELFFile
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


def read_from_elf_text_section(binary_file: IO[bytes],
                               size: int) -> Tuple[int, bytes]:
    """
    Args:
        binary_file (IO[bytes]): an opened elf file.
        size (int): number of bytes to return.
    Returns:
        tuple: (.text section offset in the binary, .text section binary code in as bytes)
    Raises:
        ELFError: if the given `binary` file is not an elf.
    """
    elf = ELFFile(binary_file)
    code = elf.get_section_by_name('.text')
    offset = code['sh_addr']
    ops = code.data()[:size]
    return offset, ops


def read_from_binary(binary_file: IO[bytes], offset: int, size: int) -> bytes:
    binary_file.seek(offset)
    return binary_file.read(size)


def is_elf_file(binary_file: IO[bytes]):
    # identifying by file's magic
    is_elf = b'\x7fELF' == binary_file.read(4)
    binary_file.seek(0)
    return is_elf


def disassemble_binary_file(
        binary_path: Path,
        arch: str,
        mode: int,
        offset: int = 0,
        size: Union[int, None] = None) -> Union[bytes, bool]:
    # TODO: In case of an elf maybe perform relocations and resolve symbols...
    with binary_path.open('rb') as bf:
        if not is_elf_file(bf):
            ops = read_from_binary(bf, offset, size)
        else:
            # disassemble elf's .text section
            try:
                (offset, ops) = read_from_elf_text_section(bf, size)
                print(
                    "Got an elf file without a specified offset, using .text section"
                )
            except ELFError:
                print("offset must be specified on non-elf binaries")
                return

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
