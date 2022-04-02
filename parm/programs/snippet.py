from typing import List

from parm.api.cursor import Cursor
from parm.api.exceptions import InvalidAccess
from parm.api.match_result import MatchResult
from parm.api.parsing.arm_asm import Instruction, ArmTransformer, Address, Block
from parm.api.parsing.arm_pat import ArmPatternTransformer
from parm.api.program import Program
from parm.api.type_hints import ReversibleIterable

from parm import parsers


class PreInitCursor(Cursor):
    def __init__(self, program, _next):
        super().__init__(program)
        self.env = program.env
        self._next = _next

    @property
    def instruction(self) -> Instruction:
        raise InvalidAccess('PreInit cursor has no instruction')

    @property
    def address(self):
        return None

    def match(self, pattern, match_result: MatchResult = None, **kwargs) -> Cursor:
        raise InvalidAccess('Nothing matches a PreInit cursor')

    def read_bytes(self, count) -> bytes:
        raise InvalidAccess('No data can be read from a PreInit cursor')

    def get_cursor_by_offset(self, offset) -> Cursor:
        raise InvalidAccess('An offset cannot be taken from a PreInit cursor')

    def next(self):
        return self._next

    def prev(self):
        raise InvalidAccess('No cursor comes before a PreInit cursor')


class PostTermCursor(Cursor):
    def __init__(self, program, prev, address=None):
        super().__init__(program)
        self.env = program.env
        self._prev = prev

        if address is not None:
            if isinstance(address, Address):
                address = address.address
            assert isinstance(address, int)
        self._address = address

    @property
    def instruction(self) -> Instruction:
        raise InvalidAccess('PostTerm cursor has no instruction')

    @property
    def address(self):
        return self._address

    def match(self, pattern, match_result: MatchResult = None, **kwargs) -> Cursor:
        raise InvalidAccess('Nothing matches a PostTerm cursor')

    def next(self):
        raise InvalidAccess('No cursor comes after a PostTerm cursor')

    def prev(self):
        return self._prev

    def read_bytes(self, count) -> bytes:
        address = self._address
        if address is None:
            raise InvalidAccess('No data can be read from an unaddressed PostTerm cursor')
        return self.program.read_bytes(address, count)

    def get_cursor_by_offset(self, offset) -> Cursor:
        address = self._address
        if address is None:
            raise InvalidAccess('An offset cannot be taken from an unaddressed PostTerm cursor')
        return self.program.create_cursor(address + offset)


class SnippetCursor(Cursor):
    def __init__(self, program, instruction=None, address=None, _prev=None, _next=None):
        super().__init__(program)
        self.env = program.env
        self._instruction = instruction
        self._address = address
        self._program = program
        self._prev = _prev
        self._next = _next

    def __str__(self):
        parts = []
        if self._address:
            parts.append(f'0x{self._address:X}: ')
        if self._instruction:
            parts.append(str(self._instruction))
        return ''.join(parts)

    def read_bytes(self, count) -> bytes:
        return self._program.read_bytes(self.address_val, count)

    def get_cursor_by_offset(self, offset) -> Cursor:
        new_address = self.address_val + offset
        return self._program.create_cursor(new_address)

    def set_prev(self, _prev):
        self._prev = _prev

    def set_next(self, _next):
        self._next = _next

    @property
    def instruction(self) -> Instruction:
        return self._instruction

    @property
    def address(self):
        adr = self._address
        if adr is None:
            return None
        assert isinstance(adr, Address)
        return adr

    @property
    def address_val(self):
        adr = self.address
        assert adr is not None
        return adr.address

    def match(self, pattern, match_result: MatchResult, **kwargs):
        return pattern.match(self, self.program, match_result, **kwargs)

    def next(self):
        return self._next

    def prev(self):
        return self._prev


class DataBlock:
    def __init__(self, address, data):
        self.start_address = address
        self.data = data

    def prepend(self, data):
        self.start_address -= len(data)
        self.data = data + self.data

    def append(self, data):
        self.data += data

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


class BlockStream:
    def __init__(self, block: DataBlock, address):
        self.block = block
        self.address = address

    def read(self, n):
        result = self.block.read_bytes(self.address, n)
        self.address += len(result)
        return result

    def tell(self):
        return self.address

    def seek(self, address):
        self.address = address


class SnippetProgram(Program):
    def __init__(self, pattern_loader, code_loader, env=None):
        super().__init__(env)
        self._pattern_loader = pattern_loader
        self._code_loader = code_loader

        self._cursors = []
        self._cursor_cache = {}
        self._data_blocks = []  # type: List[DataBlock]

    def add_data_block(self, address, data):
        try:
            block = self.find_block(address)
        except InvalidAccess:
            self._data_blocks.append(DataBlock(address, data))
            return

        start_address = address
        end_address = address + len(data)

        if block.start_address == end_address:
            block.prepend(data)
        if block.end_address == start_address:
            block.append(data)
        self._data_blocks.remove(block)
        self.add_data_block(block.start_address, block.data)

    def find_block(self, address):
        for block in self._data_blocks:
            if block.start_address <= address <= block.end_address:
                return block
        raise InvalidAccess(f'No data found for address 0x{address:X}')

    def read_bytes(self, address, size):
        block = self.find_block(address)
        if address + size > block.end_address:
            raise InvalidAccess(f'Not enough data in block {block!s} to read {size} bytes!')
        return block.read_bytes(address, size)

    def add_code_block(self, code_block, address=None):
        if isinstance(code_block, str):
            code_block = self._code_loader.load(code_block)

        code_lines = list(code_block)
        if not code_lines:
            raise ValueError('No code lines given!')

        first_line = code_lines[0]
        first_address = first_line.address
        if first_address is not None:
            if address is not None:
                if address != first_address:
                    raise ValueError('Conflicting addresses for first cursor!')
        else:
            first_address = address

        first_cursor = SnippetCursor(self, address=first_address, instruction=first_line.instruction)
        cursors = [first_cursor]
        cursors.extend([
            SnippetCursor(self, address=line.address, instruction=line.instruction)
            for line in code_lines[1:]])

        for i in range(len(cursors) - 1):
            cursors[i + 1].set_prev(cursors[i])
            cursors[i].set_next(cursors[i + 1])
        self._cursors.extend(cursors)

        term = cursors[-1]
        term.set_next(PostTermCursor(self, term, code_block.terminal))
        init = cursors[0]
        init.set_prev(PreInitCursor(self, init))

        for c in cursors:
            adr = c.address
            if adr is not None:
                assert isinstance(adr, Address)
                adr = adr.address
                assert adr not in self._cursor_cache
                self._cursor_cache[adr] = c

        return first_cursor

    def get_instruction(self, address):
        return self.create_cursor(address).instruction

    def create_cursor(self, address) -> Cursor:
        if address is None:
            raise InvalidAccess('Invalid cursor address!')
        try:
            return self._cursor_cache[address]
        except KeyError:
            try:
                self.find_block(address)
            except InvalidAccess:
                raise InvalidAccess('Failed to find cursor with address "{}"'.format(address))
            result = SnippetCursor(self, address=Address(address))
            self._cursor_cache[address] = result
            return result

    def create_pattern(self, pattern):
        return self._pattern_loader.load(pattern)

    @property
    def cursors(self) -> ReversibleIterable[Cursor]:
        return self._cursors

    def create_stream(self, cursor: Cursor):
        adr = cursor.address
        address = adr.address
        return BlockStream(self.find_block(address), address)


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

    def load(self, code_block) -> Block:
        return self.transformer.transform(self.parser.parse(code_block))


class ArmSnippetProgram(SnippetProgram):
    def __init__(self, env=None):
        super().__init__(env=env, pattern_loader=ArmPatternLoader(), code_loader=ArmCodeLoader())
