from parm.api.cursor import Cursor
from parm.api.common import default_match_result, default_env
from parm.api.match_result import MatchResult
from parm.api.parsing.arm import Instruction, ArmTransformer, Address
from parm.api.parsing.arm_pat import ArmPatternTransformer
from parm.api.program import Program
from parm.api.type_hints import ReversibleIterable

from parm import parsers


class PreInitCursor(Cursor):
    @default_env
    def __init__(self, env, _next):
        super().__init__(env)
        self._next = _next

    @property
    def instruction(self) -> Instruction:
        raise ValueError('PreInit cursor has no instruction')

    @property
    def address(self):
        return None

    def match(self, pattern, match_result: MatchResult = None) -> MatchResult:
        raise ValueError('Nothing matches a PreInit cursor')

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

    def match(self, pattern, match_result: MatchResult = None) -> MatchResult:
        raise ValueError('Nothing matches a PostTerm cursor')

    def next(self):
        raise ValueError('No cursor comes after a PostTerm cursor')

    def prev(self):
        return self._prev


class SnippetCursor(Cursor):
    def __init__(self, env, program, line, _prev=None, _next=None):
        super().__init__(env)
        self._line = line
        self._program = program
        self._prev = _prev
        self._next = _next

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
    def match(self, pattern, match_result: MatchResult) -> MatchResult:
        return pattern.match(self, self.env, match_result)

    def next(self):
        return self._next

    def prev(self):
        return self._prev


class SnippetProgram(Program):
    def __init__(self, env, pattern_loader, code_loader):
        super().__init__(env)
        self._pattern_loader = pattern_loader
        self._code_loader = code_loader

        self._cursors = []
        self._address_map = {}

    def add_code_block(self, code_block):
        if isinstance(code_block, str):
            code_block = self._code_loader.load(code_block)

        cursors = [SnippetCursor(self.env, self, line) for line in code_block]
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
                assert adr not in self._address_map
                self._address_map[adr] = c

    def get_instruction(self, address):
        return self.create_cursor(address).instruction

    def create_cursor(self, address) -> Cursor:
        if address is None:
            raise ValueError('Invalid cursor address!')
        try:
            return self._address_map[address]
        except KeyError:
            raise ValueError('Failed to find cursor with address "{}"'.format(address))

    def create_pattern(self, pattern):
        return self._pattern_loader.load(pattern)

    def find_symbol(self, symbol_name) -> Cursor:
        raise NotImplementedError()

    @property
    def cursors(self) -> ReversibleIterable[Cursor]:
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
    @default_env
    def __init__(self, env):
        super().__init__(env, pattern_loader=ArmPatternLoader(), code_loader=ArmCodeLoader())

    def find_symbol(self, symbol_name) -> Cursor:
        raise NotImplementedError()
