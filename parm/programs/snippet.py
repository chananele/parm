from typing import List

from parm.api.cursor import Cursor
from parm.api.common import default_match_result
from parm.api.match_result import MatchResult
from parm.api.parsing.arm_asm import Instruction, ArmTransformer, Address
from parm.api.parsing.arm_pat import ArmPatternTransformer
from parm.api.program import Program
from parm.api.type_hints import ReversibleIterable

from parm import parsers


class PreInitCursor(Cursor):
    def __init__(self, env, _next):
        super().__init__(env)
        self._next = _next

    @property
    def instruction(self) -> Instruction:
        raise ValueError('PreInit cursor has no instruction')

    @property
    def address(self):
        return None

    def match(self, pattern, match_result: MatchResult = None, **kwargs) -> Cursor:
        raise ValueError('Nothing matches a PreInit cursor')

    def read_bytes(self, count) -> bytes:
        raise ValueError('No data can be read from a PreInit cursor')

    def get_cursor_by_offset(self, offset) -> Cursor:
        raise ValueError('An offset cannot be taken from a PreInit cursor')

    def next(self):
        return self._next

    def prev(self):
        raise ValueError('No cursor comes before a PreInit cursor')


class PostTermCursor(Cursor):
    def __init__(self, env, _prev):
        super().__init__(env)
        self._prev = _prev

    @property
    def instruction(self) -> Instruction:
        raise ValueError('PostTerm cursor has no instruction')

    @property
    def address(self):
        return None

    def match(self, pattern, match_result: MatchResult = None, **kwargs) -> Cursor:
        raise ValueError('Nothing matches a PostTerm cursor')

    def next(self):
        raise ValueError('No cursor comes after a PostTerm cursor')

    def prev(self):
        return self._prev

    def read_bytes(self, count) -> bytes:
        raise ValueError('No data can be read from a PostTerm cursor')

    def get_cursor_by_offset(self, offset) -> Cursor:
        raise ValueError('An offset cannot be taken from a PostTerm cursor')


class SnippetCursor(Cursor):
    def __init__(self, env, program, line=None, address=None, _prev=None, _next=None):
        super().__init__(env)
        self._line = line
        self._address = address
        self._program = program
        self._prev = _prev
        self._next = _next

    def __str__(self):
        parts = []
        if self._address:
            parts.append(f'0x{self._address:X}: ')
        if self._line:
            parts.append(str(self._line))
        return ''.join(parts)

    def read_bytes(self, count) -> bytes:
        return self._program.read_bytes(self._address, count)

    def get_cursor_by_offset(self, offset) -> Cursor:
        return self._program.create_cursor(self._address + offset)

    def set_prev(self, _prev):
        self._prev = _prev

    def set_next(self, _next):
        self._next = _next

    @property
    def instruction(self) -> Instruction:
        return self._line.instruction

    @property
    def address(self):
        return self._line.address

    @default_match_result
    def match(self, pattern, match_result: MatchResult, **kwargs) -> MatchResult:
        return pattern.match(self, self.env, match_result, **kwargs)

    def next(self):
        return self._next

    def prev(self):
        return self._prev


class DataBlock:
    def __init__(self, address, data):
        self.start_address = address
        self.data = data

    @property
    def size(self):
        return len(self.data)

    @property
    def end_address(self):
        return self.start_address + self.size

    def __str__(self):
        return f'[0x{self.start_address:X}-0x{self.end_address:X}]'

    def read_bytes(self, address, count):
        offset = address - self.start_address
        result = self.data[offset: offset + count]
        assert len(result) == count
        return result


class SnippetProgram(Program):
    def __init__(self, pattern_loader, code_loader, env=None):
        super().__init__(env)
        self._pattern_loader = pattern_loader
        self._code_loader = code_loader

        self._cursors = []
        self._cursor_cache = {}
        self._data_blocks = []  # type: List[DataBlock]

    def add_data_block(self, address, data):
        self._data_blocks.append(DataBlock(address, data))

    def find_block(self, address):
        for block in self._data_blocks:
            if block.start_address <= address < block.end_address:
                return block
        raise ValueError(f'No data found for address 0x{address:X}')

    def read_bytes(self, address, size):
        block = self.find_block(address)
        if address + size > block.end_address:
            raise ValueError(f'Not enough data in block {block!s} to read {size} bytes!')
        return block.read_bytes(address, size)

    def add_code_block(self, code_block):
        if isinstance(code_block, str):
            code_block = self._code_loader.load(code_block)

        cursors = [SnippetCursor(self.env, self, line=line) for line in code_block]
        for i in range(len(cursors) - 1):
            cursors[i + 1].set_prev(cursors[i])
            cursors[i].set_next(cursors[i + 1])
        self._cursors.extend(cursors)

        term = cursors[-1]
        term.set_next(PostTermCursor(self.env, term))
        init = cursors[0]
        init.set_prev(PreInitCursor(self.env, init))

        for c in cursors:
            adr = c.address
            if adr is not None:
                assert isinstance(adr, Address)
                adr = adr.address
                assert adr not in self._cursor_cache
                self._cursor_cache[adr] = c

    def get_instruction(self, address):
        return self.create_cursor(address).instruction

    def create_cursor(self, address) -> Cursor:
        if address is None:
            raise ValueError('Invalid cursor address!')
        try:
            return self._cursor_cache[address]
        except KeyError:
            try:
                self.find_block(address)
            except ValueError:
                raise ValueError('Failed to find cursor with address "{}"'.format(address))
            result = SnippetCursor(self.env, self, address=address)
            self._cursor_cache[address] = result
            return result

    def create_pattern(self, pattern):
        return self._pattern_loader.load(pattern)

    def find_symbol(self, symbol_name) -> Cursor:
        raise NotImplementedError()

    @property
    def asm_cursors(self) -> ReversibleIterable[Cursor]:
        return self._cursors


class ArmPatternLoader:
    def __init__(self):
        self.parser = parsers.create_arm_pattern_parser()
        self.transformer = ArmPatternTransformer()

    def load(self, pattern):
        return self.transformer.transform(self.parser.parse(pattern))


class ArmCodeLoader:
    def __init__(self):
        self.parser = parsers.create_arm_parser()
        self.transformer = ArmTransformer()

    def load(self, code_block):
        return self.transformer.transform(self.parser.parse(code_block))


class ArmSnippetProgram(SnippetProgram):
    def __init__(self, env=None):
        super().__init__(env=env, pattern_loader=ArmPatternLoader(), code_loader=ArmCodeLoader())

    def find_symbol(self, symbol_name) -> Cursor:
        raise NotImplementedError()
