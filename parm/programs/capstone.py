from typing import IO, Tuple, Optional

from pathlib import Path
from capstone import CS_ARCH_ARM, CS_ARCH_X86, CS_MODE_ARM, Cs
from elftools.elf.elffile import ELFFile

from parm.api.cursor import Cursor
from parm.extensions.extension_base import magic_getter
from parm.extensions.default_extensions import AnalysisExtension
from parm.programs.snippet import ArmSnippetProgram

CAPSTONE_ARCH = {
    "arm": CS_ARCH_ARM,
    "x86": CS_ARCH_X86,  # Not supported yet
}


def translate_mode(arch, mode):
    if arch != 'arm':
        raise ValueError('Only ARM arch supported at this time')
    if mode is not None:
        if mode != 32:
            raise ValueError('Only ARM mode is currently supported')
    return CS_MODE_ARM


class CapstoneAnalysisExt(AnalysisExtension):
    @magic_getter('xrefs_to')
    def get_xrefs_to(self, cursor):
        raise NotImplementedError()

    @magic_getter('xrefs_from')
    def get_xrefs_from(self, cursor):
        raise NotImplementedError()


class CapstoneProgram(ArmSnippetProgram):
    def __init__(self, code: str = "", auto_analyze: bool = False):
        super().__init__()

        self.auto_analyze = auto_analyze
        if code:
            self.add_code_block(code)

    def register_default_extensions(self):
        super(CapstoneProgram, self).register_default_extensions()
        self.register_extension_type(CapstoneAnalysisExt)

    def find_symbol(self, symbol_name) -> Cursor:
        raise NotImplementedError()

    def _analyze(self, cursors):
        raise NotImplementedError()

    @classmethod
    def load_elf(cls, path: Path, arch: str, mode: int):
        return cls(disassemble_elf(path, arch, mode))

    @classmethod
    def load_arm_elf(cls, path: Path):
        return cls.load_elf(path, 'arm', 32)

    @classmethod
    def load_binary(cls, path: Path, arch, mode, offset=0, size=None):
        return cls(disassemble_binary(path, arch, mode, offset, size))

    @classmethod
    def load_arm_binary(cls, path: Path, offset=0, size=None):
        return cls.load_binary(path, 'arm', 32, offset, size)

    def analyze(self, cursors=None):
        if cursors is None:
            cursors = self._asm_cursors
        self._analyze(cursors)

    def add_code_block(self, add_code_block, address=None):
        before = len(self._asm_cursors)
        super().add_code_block(add_code_block, address=address)
        after = len(self._asm_cursors)

        if self.auto_analyze:
            self.analyze(self._asm_cursors[before:after])


def read_elf_text_section(binary: IO[bytes], size: int = None) -> Tuple[int, bytes]:
    """
    Read a requested number of bytes from the text section of a given elf file.


    :param binary: An open elf file
    :param size: The number of bytes to read

    :returns: A tuple containing the offset of the text section in the binary, and the requested number of bytes
        from said text section
    :raises ELFError: If the given file is not recognized as a valid elf
    """
    elf = ELFFile(binary)
    code = elf.get_section_by_name('.text')
    offset = code['sh_addr']

    ops = code.data()
    if size is not None:
        ops = ops[:size]
    return offset, ops


def is_elf_file(binary_file: IO[bytes]):
    # Identifying by file's magic
    offset = binary_file.tell()
    is_elf = b'\x7fELF' == binary_file.read(4)
    binary_file.seek(offset)
    return is_elf


def perform_disassembly(offset, ops, arch, mode):
    if not ops:
        raise ValueError("Nothing to disassemble")

    cs_arch = CAPSTONE_ARCH[arch]
    cs_mode = translate_mode(arch, mode)
    cs = Cs(cs_arch, cs_mode)
    instructions = cs.disasm(ops, offset)

    if not instructions:
        raise ValueError('Disassembly was empty!')

    return '\n'.join(f'0x{inst.address:x}: {inst.mnemonic} {inst.op_str}' for inst in instructions)


def disassemble_elf(path: Path, arch: str, mode: int):
    with path.open('rb') as bf:
        # TODO: In case of an elf maybe perform relocations and resolve symbols...
        assert is_elf_file(bf), f'File starts with {bf.read(0x10)!r}'
        offset, ops = read_elf_text_section(bf)
    return perform_disassembly(offset, ops, arch, mode)


def disassemble_binary(
        binary_path: Path,
        arch: str,
        mode: int,
        offset: int = 0,
        size: Optional[int] = None) -> str:
    with binary_path.open('rb') as bf:
        bf.seek(offset)
        ops = bf.read(size)
    return perform_disassembly(offset, ops, arch, mode)
